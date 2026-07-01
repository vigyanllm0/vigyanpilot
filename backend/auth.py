from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import bcrypt as _bcrypt
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS

def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode('utf-8'), _bcrypt.gensalt(rounds=12)).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str, role: str) -> tuple[str, str]:
    exp = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": exp,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, exp.isoformat()

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
