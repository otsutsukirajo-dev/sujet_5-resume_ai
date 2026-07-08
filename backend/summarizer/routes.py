"""
routes.py
Blueprint Flask pour le module résumé : /api/summarize et /api/history
Auteur: Mihajasoa
"""

import logging
import os
import uuid
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .extractor import ExtractionError, allowed_file, extract_text
from .summarizer import SummarizationError, summarize_text

logger = logging.getLogger(__name__)

summarizer_bp = Blueprint("summarizer_bp", __name__, url_prefix="/api")

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")


def _ensure_upload_folder():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@summarizer_bp.route("/summarize", methods=["POST"])
@jwt_required()
def summarize():
    """
    Reçoit soit un fichier (multipart/form-data, champ 'file'),
    soit du texte brut (JSON: {"text": "..."}), et renvoie un résumé.

    Réponse JSON:
        {
          "document_id": int,
          "resume_id": int,
          "summary": str,
          "original_length": int,
          "summary_length": int
        }
    """
    # Import local pour éviter les imports circulaires avec database/app
    from database.db import db
    from database.models import Document, Resume

    user_id = get_jwt_identity()

    # --- Récupération du texte source ---
    source_text = None
    filename = None

    if "file" in request.files:
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "Aucun fichier sélectionné."}), 400
        if not allowed_file(file.filename):
            return jsonify({
                "error": "Format de fichier non supporté. "
                         "Formats acceptés : .pdf, .docx, .txt"
            }), 400

        _ensure_upload_folder()
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            source_text = extract_text(filepath)
        except ExtractionError as e:
            return jsonify({"error": str(e)}), 422
        finally:
            # Nettoyage du fichier temporaire après extraction
            if os.path.exists(filepath):
                os.remove(filepath)

    elif request.is_json and request.json.get("text"):
        source_text = request.json["text"]
        filename = "texte_saisi_manuellement.txt"
    else:
        return jsonify({
            "error": "Fournissez soit un fichier ('file'), soit un champ "
                     "JSON 'text'."
        }), 400

    if not source_text or not source_text.strip():
        return jsonify({"error": "Aucun texte exploitable trouvé."}), 422

    # --- Paramètres optionnels de résumé ---
    max_length = request.form.get("max_length", type=int) or \
        (request.json.get("max_length") if request.is_json else None) or 150
    min_length = request.form.get("min_length", type=int) or \
        (request.json.get("min_length") if request.is_json else None) or 40

    # --- Génération du résumé ---
    try:
        summary = summarize_text(source_text, max_length=max_length, min_length=min_length)
    except SummarizationError as e:
        logger.error(f"Échec de résumé pour user {user_id} : {e}")
        return jsonify({"error": str(e)}), 500

    # --- Sauvegarde en base ---
    try:
        document = Document(
            filename=filename,
            content=source_text,
            user_id=user_id,
            created_at=datetime.utcnow(),
        )
        db.session.add(document)
        db.session.flush()  # récupère document.id avant le commit final

        resume = Resume(
            document_id=document.id,
            summary_text=summary,
            created_at=datetime.utcnow(),
        )
        db.session.add(resume)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur DB lors de la sauvegarde du résumé : {e}")
        return jsonify({"error": "Erreur lors de la sauvegarde du résumé."}), 500

    return jsonify({
        "document_id": document.id,
        "resume_id": resume.id,
        "summary": summary,
        "original_length": len(source_text.split()),
        "summary_length": len(summary.split()),
    }), 201


@summarizer_bp.route("/history", methods=["GET"])
@jwt_required()
def history():
    """
    Renvoie l'historique des résumés de l'utilisateur connecté.
    Query params optionnels : ?page=1&per_page=10
    """
    from database.models import Document, Resume

    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    query = (
        Resume.query
        .join(Document, Resume.document_id == Document.id)
        .filter(Document.user_id == user_id)
        .order_by(Resume.created_at.desc())
    )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = [
        {
            "resume_id": r.id,
            "document_id": r.document_id,
            "filename": r.document.filename,
            "summary": r.summary_text,
            "created_at": r.created_at.isoformat(),
        }
        for r in pagination.items
    ]

    return jsonify({
        "items": items,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
    }), 200