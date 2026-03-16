# v1.1.33
# Authentication router. Handles login, logout, and JWT token issuance.

from fastapi import APIRouter, Depends, HTTPException, Response, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.db import SessionLocal
from app.core.models import User
from app.core.security import verify_password, create_access_token
from app.api.dependencies import get_db
from app.core.ui import templates

router = APIRouter()

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...)
):
    # Search for user in the database
    user = db.query(User).filter(User.username == username).first()
    
    # Password check using the hashed_password field from the model
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Neispravno korisničko ime ili lozinka"
        })

    # Generate JWT token using uid (User ID)
    access_token = create_access_token(data={"uid": user.id})
    
    # Set cookie and redirect to dashboard
    redirect = RedirectResponse(url="/dashboard", status_code=303)
    redirect.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True,
        max_age=18000, # 5 hours
        samesite="lax"
    )
    return redirect

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response