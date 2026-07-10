# sujet_5-resume_ai
Voici notre répartition en 5 rôles complémentaires pour le projet "Résumé AI" :
👤 Personne 1 — Backend & Architecture API

Mise en place du projet Flask/FastAPI (structure, routes, config)
Définition des endpoints REST (upload, résumé, historique, export)
Gestion des erreurs et validation des données (entrées/sorties API)
Documentation de l'API (Swagger/OpenAPI)

👤 Personne 2 — Base de données & Stockage

Conception du schéma (SQLite/PostgreSQL) : utilisateurs, documents, résumés, historique
Mise en place de l'ORM (SQLAlchemy par exemple)
Stockage sécurisé des fichiers importés
Scripts de migration et de seed (données de test)

👤 Personne 3 — Authentification & Sécurité

Système d'inscription/connexion (JWT)
Gestion des rôles/permissions (utilisateur simple, admin…)
Sécurisation des routes (middleware d'auth)
Chiffrement/protection des données sensibles

👤 Personne 4 — Module IA / NLP (résumé automatique)

Intégration de transformers (pipeline de résumé, choix du modèle pré-entraîné)
Extraction de texte selon le format du fichier importé (PDF, Word, txt)
Gestion des textes longs (découpage en chunks avant résumé)
Tests de qualité des résumés générés

👤 Personne 5 — Frontend / Interface utilisateur

Interface simple (formulaire d'import, affichage des résumés, historique)
Connexion de l'interface aux endpoints de l'API
Page de connexion/inscription
Export des résultats (PDF, texte…) côté utilisateur


Coordinations :

Personnes 1 & 2  se synchroniser tôt sur le schéma de données
Personne 3 dépend des endpoints de Personne 1 pour brancher l'auth
Personne 4 peut travailler en parallèle sur un prototype isolé (notebook) avant intégration
Personne 5 a besoin que l'API soit au moins partiellement fonctionnelle pour commencer à connecter le frontend
