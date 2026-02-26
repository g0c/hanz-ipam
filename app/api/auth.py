from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette import status
from jose import JWTError

from app.core.db import SessionLocal
from app.core.models import User
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.api.dependencies import get_current_user

router = APIRouter(tags=["auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/login")
def login_form(request: Request):
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="app/templates")
    return templates.TemplateResponse("login.html", {"request": request, "title": "Prijava"})

@router.post("/login")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Neispravni podaci")

    token = create_access_token({"sub": user.username, "uid": user.id})
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=token, httponly=True, secure=False, samesite="lax", max_age=1800)
    return response

@router.get("/logout")
def logout():
    resp = RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie("access_token")
    return resp