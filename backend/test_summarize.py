"""
Script de test pour summarize_text().
Lance-le simplement avec : python test_summarize.py
(depuis le dossier backend, avec le venv active)
"""

from summarizer.summarizer import summarize_text

texte = """Dans les hautes terres de Madagascar, une nouvelle generation d'agriculteurs
commence a combiner les savoirs traditionnels avec des outils numeriques
simples. Grace a des capteurs de sol a faible cout et des applications
mobiles fonctionnant hors connexion, plusieurs cooperatives rizicoles de la
region d'Antananarivo peuvent desormais suivre l'humidite des parcelles et
anticiper les periodes de secheresse avec plusieurs jours d'avance. Cette
initiative, portee conjointement par des etudiants en informatique et des
associations paysannes locales, vise a reduire les pertes de recolte
recurrentes causees par l'irregularite des pluies.

Les premiers resultats, observes sur une saison culturale complete, montrent
une amelioration sensible du rendement dans les parcelles equipees, avec une
reduction estimee des pertes liees au stress hydrique. Les agriculteurs
impliques soulignent toutefois que la technologie ne remplace pas leur
experience du terrain, mais vient plutot la completer : les alertes generees
par les capteurs sont systematiquement croisees avec l'observation directe
des cultures avant toute decision d'irrigation.

Le principal defi reste l'acces a l'electricite et a des appareils mobiles
robustes dans les zones rurales les plus reculees. Pour y repondre, les
porteurs du projet experimentent des stations de recharge solaires
partagees, installees dans les bureaux des cooperatives, ou les
agriculteurs peuvent consulter les donnees collectives de leur zone une
fois par semaine. Les organisateurs esperent etendre le dispositif a
d'autres regions productrices de riz d'ici les prochaines saisons, sous
reserve de trouver des financements complementaires aupres de bailleurs
internationaux sensibles aux enjeux de securite alimentaire.

Des chercheurs en agronomie qui suivent le projet notent que ce type
d'initiative, bien que modeste dans son ampleur actuelle, pourrait servir de
modele replicable pour d'autres cultures vivrieres sensibles au climat,
a condition que les couts d'equipement continuent de baisser et que la
formation des utilisateurs reste une priorite constante du programme."""

print("=" * 70)
print("GENERATION DU RESUME EN COURS...")
print("=" * 70)

resume = summarize_text(texte)

print()
print("RESUME :")
print(resume)
print()
print("=" * 70)
mots_original = len(texte.split())
mots_resume = len(resume.split())
ratio = mots_resume / mots_original
print(f"Mots original : {mots_original}")
print(f"Mots resume   : {mots_resume}")
print(f"Ratio         : {ratio:.1%}  (cible : 30%-40%)")
print("=" * 70)
