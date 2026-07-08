from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from .models import db, User
from .security import hash_password, verify_password

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# --- INSCRIPTION ---
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

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

    return jsonify({"access_token": access_token, "user": user.to_dict()}), 200


# --- ROUTE PROTÉGÉE (exemple) ---
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return jsonify(user.to_dict()), 200