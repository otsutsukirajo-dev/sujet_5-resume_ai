from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from auth.blacklist import is_token_blacklisted
from flask import Flask
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from datetime import timedelta
import os
from auth.models import db
from auth.routes import auth_bp
from auth.limiter import limiter

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-moi-en-production")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)

db.init_app(app)
limiter.init_app(app)
jwt = JWTManager(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return is_token_blacklisted(jti)

app.register_blueprint(auth_bp)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, port=5000)