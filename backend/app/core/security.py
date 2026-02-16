from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings
def create_access_token(subject: str, minutes: int = 60) -> str:
    expire = datetime.utcnow() + timedelta(minutes=minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
