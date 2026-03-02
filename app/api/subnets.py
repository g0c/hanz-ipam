# v1.0.2
# API rute za upravljanje mrežnim segmentima (Subnetima)
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, get_db
from app.services import subnet_service
from app.services.flash import flash

router = APIRouter(tags=["subnets"])
templates = Jinja2Templates(directory="app/templates")

# Dohvaćanje liste svih subneta s izračunatom statistikom
@router.get("/")
def list_subnets(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    subnets = subnet_service.get_all_subnets_with_stats(db)
    return templates.TemplateResponse("subnets_list.html", {"request": request, "subnets": subnets, "user": user})

# Dodavanje novog subneta (Sada podržava naziv i VLAN)
@router.post("/add")
def add_subnet(
    request: Request,
    cidr: str = Form(...), 
    name: str = Form(None),
    vlan_id: int = Form(None),
    description: str = Form(None), 
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    try:
        subnet_service.create_subnet(db, cidr=cidr, name=name, vlan_id=vlan_id, description=description)
        resp = RedirectResponse(url="/subnets", status_code=303)
        return flash(resp, "Novi subnet je uspješno dodan!")
    except Exception as e:
        # Ako CIDR nije ispravan, vraćamo korisnika na listu s porukom o grešci
        subnets = subnet_service.get_all_subnets_with_stats(db)
        return templates.TemplateResponse("subnets_list.html", {
            "request": request, "subnets": subnets, "user": user, "error": f"Greška kod unosa: {str(e)}"
        })

# Prikaz IP mape za odabrani subnet
@router.get("/{subnet_id}")
def view_subnet(subnet_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    data = subnet_service.get_subnet_map(db, subnet_id)
    if not data:
        raise HTTPException(status_code=404, detail="Subnet nije pronađen")
    return templates.TemplateResponse("subnets_view.html", {"request": request, "data": data, "user": user})

# Prikaz HTML forme za uređivanje postojećeg subneta
@router.get("/{subnet_id}/edit")
def edit_subnet_form(subnet_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    subnet = subnet_service.get_subnet(db, subnet_id)
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet nije pronađen")
    return templates.TemplateResponse("subnets_edit.html", {"request": request, "subnet": subnet, "user": user})

# Spremanje promjena nakon uređivanja subneta
@router.post("/{subnet_id}/edit")
def edit_subnet(
    subnet_id: int,
    request: Request,
    cidr: str = Form(...),
    name: str = Form(None),
    vlan_id: int = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        subnet_service.update_subnet(db, subnet_id, name=name, cidr=cidr, vlan_id=vlan_id, description=description)
        resp = RedirectResponse(url="/subnets", status_code=303)
        return flash(resp, "Promjene u subnetu su uspješno spremljene!")
    except Exception as e:
        # Vraćamo formu za uređivanje u slučaju greške (npr. neispravan CIDR format)
        subnet = subnet_service.get_subnet(db, subnet_id)
        return templates.TemplateResponse("subnets_edit.html", {
            "request": request, "subnet": subnet, "user": user, "error": str(e)
        })