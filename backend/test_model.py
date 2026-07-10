from transformers import pipeline

p = pipeline('summarization', model='facebook/bart-large-cnn')

texte = """Ceci est un texte de test suffisamment long pour verifier que le modele fonctionne correctement apres un nouveau telechargement complet, sans interruption cette fois, en esperant que la connexion tienne le coup jusqu'au bout du processus. Ce texte doit contenir assez de mots pour que le resume produise un resultat coherent et verifiable."""

resultat = p(texte, max_length=60, min_length=20)
print(resultat)