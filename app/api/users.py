# v1.0.0
# API router for user management and administration.

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.api.dependencies import get_current_user, get_db
from app.core.models import User
from app.core.ui import templates
from app.services import audit_service

router = APIRouter(tags=["users"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get("/")
def list_users(
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """List all users in the system. Admin only."""
    if current_user.role != "admin":
        return RedirectResponse(url="/", status_code=303)
    
    users = db.query(User).all()
    return templates.TemplateResponse("users_list.html", {
        "request": request,
        "user": current_user,
        "users": users,
        "title": "User Management"
    })

@router.get("/add")
def add_user_page(request: Request, current_user: User = Depends(get_current_user)):
    """Render the page to add a new user."""
    if current_user.role != "admin":
        return RedirectResponse(url="/", status_code=303)
        
    return templates.TemplateResponse("users_add.html", {
        "request": request, 
        "user": current_user, 
        "title": "Add User"
    })

@router.post("/add")
def create_user(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Handle the creation of a new user in the database."""
    if current_user.role != "admin":
        return RedirectResponse(url="/", status_code=303)

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return templates.TemplateResponse("users_add.html", {
            "request": request, 
            "user": current_user, 
            "error": "Username is already taken!"
        })

    hashed_pwd = pwd_context.hash(password)
    new_user = User(
        username=username,
        full_name=full_name,
        hashed_password=hashed_pwd,
        role=role,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    
    audit_service.log_event(
        db=db, 
        username=current_user.username, 
        action="CREATE", 
        target_type="USER", 
        target_id=new_user.id, 
        details=f"Created new user: {username}"
    )
    
    return RedirectResponse(url="/users", status_code=303)