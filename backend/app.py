import os
from flask import Flask
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from datetime import timedelta

from database.db import init_db
from auth.routes import auth_bp
from auth.limiter import limiter
from auth.blacklist import is_token_blacklisted

load_dotenv()


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True, allow_headers=["Content-Type", "Authorization"])

    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'change-moi-en-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

    # Initialise la config DB, db.init_app(app) ET db.create_all() en une fois
    init_db(app)

    limiter.init_app(app)
    jwt = JWTManager(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        return is_token_blacklisted(jti)

    app.register_blueprint(auth_bp)

    # --- ZONE DE CONNEXION POUR MANDRESY ET MIHAJASOA ---
    # C'est ici que leurs blueprints seront enregistrés plus tard.

    @app.route('/')
    def index():
        return {
            "status": "success",
            "message": "L'architecture backend fonctionne !"
        }

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000, host="0.0.0.0")