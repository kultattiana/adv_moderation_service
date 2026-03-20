import hashlib
import hmac
import secrets

def hash_password(password: str, salt: str = None) -> str:
   
    if salt:
        salted = password + salt
    else:
        salted = password
    
    hashed = hashlib.md5(salted.encode('utf-8')).hexdigest()
    
    return hashed

def verify_password(plain_password: str, hashed_password: str, salt: str=None) -> bool:

    return hmac.compare_digest(
        hash_password(plain_password, salt),
        hashed_password
    )

def generate_salt() -> str:
    return secrets.token_hex(16)