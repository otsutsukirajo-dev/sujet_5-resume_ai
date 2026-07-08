import os
from flask import Flask
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

    jwt = JWTManager(app)

    @app.route('/')
    def test_serveur():
        return {"statut": "En ligne", "message": "Serveur central prêt !"}

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)