from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    """
    Configure et initialise la base de données pour l'app Flask.
    À appeler depuis app.py après la création de l'app.
    """
    app.config.setdefault(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///app.db"
    )
    app.config.setdefault(
        "SQLALCHEMY_TRACK_MODIFICATIONS", False
    )
    db.init_app(app)

    with app.app_context():
        db.create_all()