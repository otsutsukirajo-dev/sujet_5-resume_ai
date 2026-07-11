sujet_5-resume_ai

Répartition des tâches

Voici notre répartition en 5 rôles complémentaires pour le projet "Résumé AI" :

 RAJO — Backend & Architecture API
- Mise en place du projet Flask/FastAPI (structure, routes, config)
- Définition des endpoints REST (upload, résumé, historique, export)
- Gestion des erreurs et validation des données (entrées/sorties API)
- Documentation de l'API (Swagger/OpenAPI)

 MANDRESY — Base de données & Stockage
- Conception du schéma (SQLite/PostgreSQL) : utilisateurs, documents, résumés, historique
- Mise en place de l'ORM (SQLAlchemy)
- Stockage sécurisé des fichiers importés
- Scripts de migration et de seed (données de test)

 MEDDY — Authentification & Sécurité
- Système d'inscription/connexion (JWT)
- Gestion des rôles/permissions (utilisateur simple, admin…)
- Sécurisation des routes (middleware d'auth)
- Chiffrement/protection des données sensibles

 MIHAJASOA — Module IA / NLP (résumé automatique)
- Intégration de Transformers (pipeline de résumé, choix du modèle pré-entraîné)
- Extraction de texte selon le format du fichier importé (PDF, Word, TXT)
- Gestion des textes longs (découpage en sous-parties avant résumé)
- Tests de qualité des résumés générés

 FENO — Frontend / Interface utilisateur
- Interface simple (formulaire d'import, affichage des résumés, historique)
- Connexion de l'interface aux endpoints de l'API
- Page de connexion/inscription
- Export des résultats (PDF, texte…) côté utilisateur

### Coordination
- RAJO et MANDRESY se sont synchronisés tôt sur le schéma de données
- MEDDY dépend des endpoints de RAJO pour brancher l'authentification
- MIHAJASOA a pu travailler en parallèle sur un prototype isolé (notebook) avant intégration
- FENO a eu besoin que l'API soit au moins partiellement fonctionnelle pour commencer à connecter le frontend

---

## ⚠️ Avant de tester le module de résumé IA (important)

Le module IA repose sur 3 modèles pré-entraînés (Hugging Face) qui ne sont **pas inclus dans ce dépôt** (trop volumineux pour GitHub, limite de 100 Mo par fichier). Ils se téléchargent **automatiquement** au premier lancement.

**⚠️ Prévoir environ 2,2 Go de téléchargement et une connexion internet stable au premier test.**

| Modèle | Rôle | Taille |
|---|---|---|
| `facebook/bart-large-cnn` | Génération du résumé | ~1,6 Go |
| `Helsinki-NLP/opus-mt-fr-en` | Traduction FR → EN | ~300 Mo |
| `Helsinki-NLP/opus-mt-en-fr` | Traduction EN → FR | ~300 Mo |

**Pour éviter tout blocage pendant le test**, lancez d'abord ce script de préchauffage, qui télécharge les 3 modèles une fois pour toutes (le premier résumé sera ensuite instantané, même hors connexion) :

```bash
cd backend
venv\Scripts\activate      # ou source venv/bin/activate sous Linux/Mac
pip install -r requirements.txt
python warmup_models.py
```

Une fois ce script terminé, l'application peut être lancée normalement (`python app.py`) et générer des résumés sans délai de téléchargement.
