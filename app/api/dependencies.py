from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.core.db import SessionLocal
from app.core.models import User
from app.core.config import settings

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Nedostaje token")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        uid = payload.get("uid")
    except JWTError:
        raise HTTPException(status_code=401, detail="Neispravan token")

    user = db.query(User).filter(User.id == uid).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Korisnik neaktivan ili ne postoji")
    return user