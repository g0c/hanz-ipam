# v1.1.0
# Ruter za upravljanje mrežnim segmentima (Subnets) - IPAM modul.

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import ipaddress

from app.api.dependencies import get_current_user, get_db
from app.services import subnet_service
from app.services.flash import flash
from app.core.ui import templates  # Korištenje centralnog UI objekta

from fastapi import BackgroundTasks
from app.services import discovery_service 

router = APIRouter(tags=["subnets"])

@router.post("/{subnet_id}/scan")
def trigger_scan(subnet_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    Pokreće skeniranje podmreže u pozadini kako ne bi blokiralo UI.
    """
    background_tasks.add_task(discovery_service.run_subnet_scan, db, subnet_id)
    resp = RedirectResponse(url=f"/subnets/{subnet_id}", status_code=303)
    return flash(resp, "Skeniranje podmreže pokrenuto u pozadini. Osvježite stranicu za par trenutaka.")

# --- LISTA PODMREŽA ---
@router.get("/")
def list_subnets(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Dohvaćanje svih podmreža s izračunatim postotkom iskorištenja
    subnets = subnet_service.get_subnets_with_usage(db)
    return templates.TemplateResponse(request=request, name="subnets_list.html", context={"subnets": subnets,
        "user": user})

# --- DODAVANJE NOVE PODMREŽE ---
@router.post("/add")
def add_subnet(
    request: Request,
    name: str = Form(...),
    cidr: str = Form(...),
    vlan_id: int = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        # Validacija CIDR zapisa prije pokušaja spremanja
        ipaddress.ip_network(cidr)
        
        # Spremanje u bazu (sada uključuje name i vlan_id)
        subnet_service.create_subnet(
            db, 
            name=name, 
            cidr=cidr, 
            vlan_id=vlan_id, 
            description=description
        )
        
        resp = RedirectResponse(url="/subnets", status_code=303)
        return flash(resp, f"Podmreža {name} je uspješno kreirana!")
        
    except ValueError:
        # Greška ako CIDR nije ispravan (npr. 192.168.1.5/24 umjesto .0/24)
        subnets = subnet_service.get_subnets_with_usage(db)
        return templates.TemplateResponse(request=request, name="subnets_list.html", context={"subnets": subnets,
            "user": user,
            "error": "Neispravna CIDR notacija! Provjerite bazu mreže (npr. .0/24)."})
    except Exception as e:
        subnets = subnet_service.get_subnets_with_usage(db)
        return templates.TemplateResponse(request=request, name="subnets_list.html", context={"subnets": subnets,
            "user": user,
            "error": f"Greška pri spremanju: {str(e)}"})

# --- VIZUALNI PREGLED (IP MAPA) ---
@router.get("/{subnet_id}")
def view_subnet(subnet_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Generira mapu svih IP adresa unutar segmenta
    data = subnet_service.get_subnet_map(db, subnet_id)
    if not data:
        raise HTTPException(status_code=404, detail="Podmreža nije pronađena")
        
    return templates.TemplateResponse(request=request, name="subnets_view.html", context={"data": data,
        "user": user})

# --- UREĐIVANJE PODMREŽE ---
@router.get("/{subnet_id}/edit")
def edit_subnet_form(subnet_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    subnet = subnet_service.get_subnet(db, subnet_id)
    if not subnet:
        raise HTTPException(status_code=404, detail="Podmreža nije pronađena")
        
    return templates.TemplateResponse(request=request, name="subnets_edit.html", context={"subnet": subnet,
        "user": user})

@router.post("/{subnet_id}/edit")
def update_subnet(
    subnet_id: int,
    request: Request,
    name: str = Form(...),
    cidr: str = Form(...),
    vlan_id: int = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        ipaddress.ip_network(cidr)
        subnet_service.update_subnet(db, subnet_id, name, cidr, vlan_id, description)
        
        resp = RedirectResponse(url="/subnets", status_code=303)
        return flash(resp, "Promjene na podmreži su uspješno spremljene!")
        
    except Exception as e:
        subnet = subnet_service.get_subnet(db, subnet_id)
        return templates.TemplateResponse(request=request, name="subnets_edit.html", context={"subnet": subnet,
            "user": user,
            "error": f"Ažuriranje neuspješno: {str(e)}"})