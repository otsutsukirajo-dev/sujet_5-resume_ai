from flask import Flask
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

from auth.models import db
from auth.routes import auth_bp

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-moi-en-production")

db.init_app(app)
jwt = JWTManager(app)

app.register_blueprint(auth_bp)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, port=5000)