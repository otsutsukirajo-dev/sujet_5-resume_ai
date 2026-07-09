from datetime import datetime
from auth.models import db

class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "uploaded_at": self.uploaded_at.isoformat(),
            "user_id": self.user_id
        }


class Summary(db.Model):
    __tablename__ = "summaries"

    id = db.Column(db.Integer, primary_key=True)
    summary_text = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "summary_text": self.summary_text,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat(),
            "document_id": self.document_id
        }


class Historique(db.Model):
    __tablename__ = "historique"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "created_at": self.created_at.isoformat(),
            "user_id": self.user_id
        }