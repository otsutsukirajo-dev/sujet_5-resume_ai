"""
Script de PRECHAUFFAGE des modeles IA.

A lancer UNE FOIS, a l'avance (pas le jour de la demo/soutenance), sur
chaque machine qui va faire tourner le projet : la tienne, celles de tes
coequipiers, et surtout la machine qui servira le jour de l'evaluation
si ce n'est pas la meme.

Ca telecharge et met en cache les 3 modeles IA (BART + les 2 modeles de
traduction) SANS avoir besoin de lancer Flask ni de resumer un vrai
document. Une fois termine, tout est en cache local et le premier resume
en vrai sera instantane, meme sans connexion internet ce jour-la.

Usage :
    cd backend
    venv\\Scripts\\activate
    python warmup_models.py
"""

import sys
import time

print("=" * 70)
print("PRECHAUFFAGE DES MODELES IA - Resume AI")
print("=" * 70)
print("Ceci va telecharger environ 2.2 Go au total (une seule fois).")
print("Prevoir du temps selon la connexion. Ne pas interrompre.")
print("=" * 70)
print()

try:
    from summarizer.summarizer import (
        _get_summary_pipeline,
        _get_translation_pipeline,
        SUMMARY_MODEL_NAME,
        TRANSLATION_MODEL_FR_EN,
        TRANSLATION_MODEL_EN_FR,
    )
except ImportError as e:
    print(f"ERREUR : impossible d'importer summarizer.py ({e})")
    print("Verifie que tu es bien dans le dossier backend/ avec le venv active.")
    sys.exit(1)

etapes = [
    ("Modele de resume (BART, ~1.6 Go)", lambda: _get_summary_pipeline(SUMMARY_MODEL_NAME)),
    ("Modele de traduction FR->EN (~300 Mo)", lambda: _get_translation_pipeline(TRANSLATION_MODEL_FR_EN)),
    ("Modele de traduction EN->FR (~300 Mo)", lambda: _get_translation_pipeline(TRANSLATION_MODEL_EN_FR)),
]

for nom, charger in etapes:
    print(f"-> Chargement : {nom}...")
    debut = time.time()
    try:
        charger()
        duree = time.time() - debut
        print(f"   OK ({duree:.1f}s)")
    except Exception as e:
        print(f"   ECHEC : {e}")
        print("   Reessaie de lancer ce script, ou verifie ta connexion.")
        sys.exit(1)
    print()

print("=" * 70)
print("TERMINE. Les 3 modeles sont maintenant en cache local.")
print("Le projet peut desormais generer des resumes sans telecharger quoi")
print("que ce soit, meme hors connexion.")
print("=" * 70)
