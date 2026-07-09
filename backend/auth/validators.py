import re
from email_validator import validate_email, EmailNotValidError

def is_valid_email(email: str) -> tuple[bool, str]:
    try:
        validate_email(email, check_deliverability=False)
        return True, ""
    except EmailNotValidError as e:
        return False, str(e)

def is_strong_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères"
    if not re.search(r"[A-Z]", password):
        return False, "Le mot de passe doit contenir au moins une majuscule"
    if not re.search(r"[a-z]", password):
        return False, "Le mot de passe doit contenir au moins une minuscule"
    if not re.search(r"[0-9]", password):
        return False, "Le mot de passe doit contenir au moins un chiffre"
    return True, ""