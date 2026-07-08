import os
from flask import Flask
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager
from flask_cors import CORS

# On importe les modules de sécurité et la base de données depuis le dossier auth/ de Damon
from auth.models import db
from auth.routes import auth_bp
from auth.limiter import limiter
from auth.blacklist import is_token_blacklisted

load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Configuration de l'application (Orthographe corrigée !)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

    # Initialisation de la base de données unique (Règle de Damon)
    db.init_app(app)
    
    # Initialisation du limiteur de requêtes de sécurité
    limiter.init_app(app)

    # Configuration du gestionnaire de Jetons JWT
    jwt = JWTManager(app)

    # Liaison de la liste noire de jetons de Damon
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return is_token_blacklisted(jwt_payload)

    # Enregistrement du morceau d'API (Blueprint) de Damon
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # --- ZONE DE CONNEXION POUR MANDRESY ET MIHAJASOA ---
    # C'est ici que tu placeras leurs routes plus tard.

    # Création automatique de la base de données SQLite au démarrage
    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        return {
            "status": "success", 
            "message": "Félicitations Rajo, l'architecture clonée et sécurisée fonctionne !"
        }

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)