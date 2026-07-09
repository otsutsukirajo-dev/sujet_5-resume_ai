import os
from datetime import timedelta
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv

# --- Import des composants du module AUTH (Meddy) ---
from auth.models import db
from auth.routes import auth_bp
from auth.blacklist import is_token_blacklisted
from auth.limiter import limiter

# --- Import des autres modules branchés ---
# from database.models import Document, Resume   # Laissé pour Mandresy
from summarizer.routes import summarizer_bp     # Activé pour Mihajasoa

load_dotenv()

app = Flask(__name__)

# --- Config générale (Sécurisée via le .env) ---
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-moi-en-production")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)

# --- Initialisation des extensions (UNE SEULE FOIS) ---
CORS(app)
db.init_app(app)
jwt = JWTManager(app)
limiter.init_app(app)

# --- Callback blacklist JWT conforme au fichier INTEGRATION.md ---
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]  # Extraction demandée par Meddy
    return is_token_blacklisted(jti)

# --- Enregistrement des blueprints conforme au fichier INTEGRATION.md ---
app.register_blueprint(auth_bp)
app.register_blueprint(summarizer_bp)  # Enregistré avec succès !

# --- Création des tables ---
with app.app_context():
    db.create_all()

# Route racine pour tester facilement sur ton navigateur
@app.route('/')
def index():
    return {
        "status": "success", 
        "message": "L'API centrale de Rajo tourne parfaitement ! Auth et Summarizer sont synchronisés."
    }

if __name__ == "__main__":
    app.run(debug=True, port=5000)