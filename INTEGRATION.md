#  Guide d'intégration — Module Authentification & Sécurité

**Auteur du module :** Meddy (Personne 3)
**Dossier concerné :** `backend/auth/`
**Repo :** `sujet_5-resume_ai`

Ce document explique comment chaque membre de l'équipe doit intégrer son travail avec le module d'authentification pour que tout fonctionne ensemble sans conflit.

---

##  Ce que le module `auth/` fournit

| Élément | Fichier | Description |
|---|---|---|
| `db` | `auth/models.py` | Instance SQLAlchemy — **à réutiliser partout**, ne jamais en recréer une deuxième |
| `User` | `auth/models.py` | Modèle utilisateur (id, email, password_hash, role, created_at) |
| `auth_bp` | `auth/routes.py` | Blueprint Flask avec toutes les routes d'authentification |
| `limiter` | `auth/limiter.py` | Instance Flask-Limiter (anti brute-force) |
| `is_token_blacklisted` | `auth/blacklist.py` | Fonction de vérification des tokens révoqués (logout) |

### Routes disponibles

| Route | Méthode | Auth requise | Body (JSON) | Réponse succès |
|---|---|---|---|---|
| `/auth/register` | POST | Non | `{"email", "password"}` | `{"message", "user"}` |
| `/auth/login` | POST | Non | `{"email", "password"}` | `{"access_token", "refresh_token", "user"}` |
| `/auth/me` | GET | Oui (Bearer) | — | `{"id", "email", "role", "created_at"}` |
| `/auth/refresh` | POST | Oui (Bearer refresh_token) | — | `{"access_token"}` |
| `/auth/logout` | POST | Oui (Bearer) | — | `{"message"}` |
| `/auth/change-password` | POST | Oui (Bearer) | `{"old_password", "new_password"}` | `{"message"}` |

**Règles de mot de passe :** min. 8 caractères, 1 majuscule, 1 minuscule, 1 chiffre.
**Anti brute-force :** max 5 tentatives de connexion par minute par IP (erreur 429 au-delà).

---

##  Rjo — Backend & Architecture API (app.py principal)

Ton `app.py` final doit importer et assembler tous les modules, sans rien recréer en double.

### Dépendances à installer
```bash
pip install flask flask-sqlalchemy flask-jwt-extended bcrypt python-dotenv email-validator flask-limiter flask-cors
```
(ou plus simple : `pip install -r requirements.txt`)

### Structure de `app.py`

```python
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import timedelta
import os

# --- Import des composants du module AUTH (Meddy) ---
from auth.models import db
from auth.routes import auth_bp
from auth.blacklist import is_token_blacklisted
from auth.limiter import limiter

# --- Import des autres modules ---
# from database.models import Document, Resume   # Mandresy
# from summarizer.routes import summarizer_bp     # Mihajasoa

load_dotenv()

app = Flask(__name__)

# --- Config générale ---
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-moi-en-production")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)

# --- Initialisation des extensions (UNE SEULE FOIS) ---
CORS(app)
db.init_app(app)
jwt = JWTManager(app)
limiter.init_app(app)

# --- Callback blacklist JWT (obligatoire pour que logout fonctionne) ---
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return is_token_blacklisted(jti)

# --- Enregistrement des blueprints ---
app.register_blueprint(auth_bp)
# app.register_blueprint(summarizer_bp)   # à ajouter

# --- Création des tables ---
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

###  Points de vigilance
1. **Un seul `db`** — jamais `SQLAlchemy()` recréé ailleurs.
2. **Un seul `JWTManager`**.
3. **Ordre important** : `db.init_app(app)` avant `db.create_all()`, blueprints enregistrés avant `app.run()`.
4. Le nom exact du blueprint de Mihajasoa à enregistrer est `summarizer_bp`.

---

##  Mandresy — Base de données & Stockage

### Règle la plus importante
Ne jamais créer un deuxième `SQLAlchemy()`. Importer et réutiliser le `db` existant.

### Modèle `User` existant (référence)
```python
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### Exemple de `database/models.py`

```python
from auth.models import db, User   # réutiliser le même db
from datetime import datetime

class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="documents")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "uploaded_at": self.uploaded_at.isoformat(),
            "user_id": self.user_id
        }


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    document = db.relationship("Document", backref="resumes")

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="resumes")

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "document_id": self.document_id,
            "user_id": self.user_id
        }
```

###  Points de vigilance
1. Toujours `from auth.models import db, User` — jamais recréer `db`.
2. Le nom de table de `User` est `users` → `db.ForeignKey("users.id")`.
3. Récupérer l'utilisateur connecté avec `get_jwt_identity()` dans les routes protégées.
4. `db.create_all()` est appelé une seule fois par Rjo dans `app.py` final — retirer tout `create_all()` de test avant le merge.

---

##  Mihajasoa — Module IA / NLP (résumé automatique)

### Dépendance à installer
```bash
pip install flask-jwt-extended
```

### Exemple de `summarizer/routes.py`

```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from auth.models import db, User
from database.models import Document, Resume
from .summarizer import generate_summary
from .extractor import extract_text_from_file

summarizer_bp = Blueprint("summarizer", __name__, url_prefix="/api")


@summarizer_bp.route("/summarize", methods=["POST"])
@jwt_required()
def summarize():
    user_id = get_jwt_identity()

    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier fourni"}), 400

    file = request.files["file"]
    text = extract_text_from_file(file)

    document = Document(
        filename=file.filename,
        filepath="",
        user_id=user_id
    )
    db.session.add(document)
    db.session.commit()

    summary_text = generate_summary(text)

    resume = Resume(
        content=summary_text,
        document_id=document.id,
        user_id=user_id
    )
    db.session.add(resume)
    db.session.commit()

    return jsonify({
        "message": "Résumé généré avec succès",
        "resume": resume.to_dict()
    }), 201


@summarizer_bp.route("/history", methods=["GET"])
@jwt_required()
def get_history():
    user_id = get_jwt_identity()
    resumes = Resume.query.filter_by(user_id=user_id).order_by(Resume.created_at.desc()).all()
    return jsonify([r.to_dict() for r in resumes]), 200
```

###  Points de vigilance
1. Toujours `@jwt_required()` sur les routes du module.
2. `get_jwt_identity()` retourne l'id sous forme de `str` — attention si conversion nécessaire.
3. Import propre : `from auth.models import db, User` et `from database.models import Document, Resume`.
4. Le blueprint doit s'appeler exactement `summarizer_bp` pour que Rjo l'enregistre correctement.
5. Gérer les erreurs IA (texte trop long, format non supporté) avec `try/except`.

---

##  Feno — Frontend / Interface utilisateur

### Base URL de l'API (en local)
```
http://localhost:5000/auth
```

CORS est activé côté backend, donc les appels depuis le frontend fonctionnent sans blocage navigateur.

### Codes d'erreur à gérer

| Code | Signification | Action recommandée |
|---|---|---|
| 400 | Données invalides | Afficher le message d'erreur du champ concerné |
| 401 | Non authentifié / token expiré | Appeler `/auth/refresh`, sinon rediriger vers login |
| 409 | Email déjà utilisé | Afficher message sur le formulaire d'inscription |
| 429 | Trop de tentatives | Afficher "Trop d'essais, réessayez dans 1 minute" |

### Exemples de code JavaScript

**Inscription :**
```javascript
const res = await fetch("http://localhost:5000/auth/register", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, password })
});
const data = await res.json();
if (!res.ok) {
  // data.error contient le message d'erreur
}
```

**Connexion + stockage des tokens :**
```javascript
const res = await fetch("http://localhost:5000/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, password })
});
const data = await res.json();
localStorage.setItem("access_token", data.access_token);
localStorage.setItem("refresh_token", data.refresh_token);
```

**Appel d'une route protégée :**
```javascript
const token = localStorage.getItem("access_token");
const res = await fetch("http://localhost:5000/auth/me", {
  headers: { "Authorization": `Bearer ${token}` }
});
```

**Rafraîchir le token si expiré (401) :**
```javascript
async function refreshAccessToken() {
  const refreshToken = localStorage.getItem("refresh_token");
  const res = await fetch("http://localhost:5000/auth/refresh", {
    method: "POST",
    headers: { "Authorization": `Bearer ${refreshToken}` }
  });
  const data = await res.json();
  localStorage.setItem("access_token", data.access_token);
  return data.access_token;
}
```

**Déconnexion :**
```javascript
const token = localStorage.getItem("access_token");
await fetch("http://localhost:5000/auth/logout", {
  method: "POST",
  headers: { "Authorization": `Bearer ${token}` }
});
localStorage.removeItem("access_token");
localStorage.removeItem("refresh_token");
```

---

##  Le merge final

- [ ] Tout le monde utilise le même `db` (importé depuis `auth/models.py`)
- [ ] Un seul `JWTManager`, un seul `Limiter`, un seul `CORS(app)`
- [ ] `requirements.txt` à jour avec toutes les dépendances du groupe
- [ ] Toutes les routes sensibles protégées par `@jwt_required()`
- [ ] `db.create_all()` appelé une seule fois, dans `app.py` final (par Rjo)
- [ ] `.env` jamais commité (vérifier `.gitignore`)
- [ ] Chaque branche `feature/...` mergée via Pull Request, avec review si possible
