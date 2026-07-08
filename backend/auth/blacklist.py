# Liste noire simple en mémoire (pour un vrai projet en production, utiliser Redis)
BLACKLIST = set()

def add_token_to_blacklist(jti: str):
    BLACKLIST.add(jti)

def is_token_blacklisted(jti: str) -> bool:
    return jti in BLACKLIST