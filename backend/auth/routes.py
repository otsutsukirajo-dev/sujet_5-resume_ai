from .limiter import limiter
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from .models import db, User
from .security import hash_password, verify_password
from .validators import is_valid_email, is_strong_password
from .blacklist import add_token_to_blacklist

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# --- INSCRIPTION ---
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    valid_email, email_error = is_valid_email(email)
    if not valid_email:
        return jsonify({"error": email_error}), 400

    valid_pwd, pwd_error = is_strong_password(password)
    if not valid_pwd:
        return jsonify({"error": pwd_error}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Cet email est déjà utilisé"}), 409

    new_user = User(
        email=email,
        password_hash=hash_password(password),
        role="user"
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Utilisateur créé", "user": new_user.to_dict()}), 201

# --- CONNEXION ---

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not verify_password(password, user.password_hash):
        return jsonify({"error": "Identifiants invalides"}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "email": user.email}
    )
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    }), 200

# --- ROUTE PROTÉGÉE (exemple) ---
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return jsonify(user.to_dict()), 200

# --- RAFRAÎCHIR LE TOKEN ---

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    new_access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "email": user.email}
    )

    return jsonify({"access_token": new_access_token}), 200

# --- DÉCONNEXION ---
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    add_token_to_blacklist(jti)
    return jsonify({"message": "Déconnexion réussie"}), 200

# --- CHANGEMENT DE MOT DE PASSE ---
@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    data = request.get_json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        return jsonify({"error": "Ancien et nouveau mot de passe requis"}), 400

    if not verify_password(old_password, user.password_hash):
        return jsonify({"error": "Ancien mot de passe incorrect"}), 401

    valid_pwd, pwd_error = is_strong_password(new_password)
    if not valid_pwd:
        return jsonify({"error": pwd_error}), 400

    user.password_hash = hash_password(new_password)
    db.session.commit()

    return jsonify({"message": "Mot de passe modifié avec succès"}), 200