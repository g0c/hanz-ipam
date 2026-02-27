# v1.0.1
from fastapi import APIRouter, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, get_db
from app.services import subnet_service

router = APIRouter(tags=["subnets"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
def list_subnets(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    subnets = subnet_service.get_all_subnets_with_stats(db)
    return templates.TemplateResponse("subnets_list.html", {"request": request, "subnets": subnets, "user": user})

@router.post("/add")
def add_subnet(cidr: str = Form(...), description: str = Form(None), db: Session = Depends(get_db), user=Depends(get_current_user)):
    subnet_service.create_subnet(db, cidr, description)
    return RedirectResponse(url="/subnets", status_code=303)

@router.get("/{subnet_id}")
def view_subnet(subnet_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    data = subnet_service.get_subnet_map(db, subnet_id)
    return templates.TemplateResponse("subnets_view.html", {"request": request, "data": data, "user": user})