# v1.0.2
# Sigurnosne funkcije za hashiranje lozinki i generiranje JWT tokena.

from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # Generira hash lozinke koristeći bcrypt
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    # Provjerava odgovara li unesena lozinka spremljenom hashu
    return pwd_context.verify(password, password_hash)

def create_access_token(data: dict, expires_minutes: int | None = None):
    to_encode = data.copy()
    
    # Postavljamo trajanje tokena na 7 dana (10080 minuta) 
    # ako u pozivu funkcije nije specifično zatraženo drugačije
    expire_time = expires_minutes if expires_minutes is not None else 10080
    
    expire = datetime.utcnow() + timedelta(minutes=expire_time)
    to_encode.update({"exp": expire})
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")