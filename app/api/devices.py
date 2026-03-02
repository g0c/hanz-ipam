# v1.0.9
# API rute za upravljanje uređajima - Komentari na hrvatskom jeziku.

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_current_user, get_db
from app.services import device_service, subnet_service
from app.services.flash import flash

router = APIRouter(tags=["devices"])
templates = Jinja2Templates(directory="app/templates")

# --- LISTA UREĐAJA ---
@router.get("/")
def list_devices(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Dohvaćanje svih uređaja za glavni prikaz tablice
    devices = device_service.get_all_devices(db)
    return templates.TemplateResponse("devices_list.html", {
        "request": request, 
        "devices": devices,
        "user": user
    })

# --- DODAVANJE UREĐAJA ---
@router.get("/add")
def add_device_form(
    request: Request, 
    ip: str = None, 
    subnet_id: int = None, 
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    # Dohvaćamo subnete za dropdown izbornik u formi
    subnets = db.query(subnet_service.Subnet).all()
    return templates.TemplateResponse("devices_add.html", {
        "request": request,
        "user": user,
        "prefilled_ip": ip,
        "prefilled_subnet": subnet_id,
        "subnets": subnets
    })

@router.post("/add")
def add_device(
    request: Request,
    hostname: str = Form(...),
    ip_addr: str = Form(...),
    status: str = Form("unknown"),
    device_type: str = Form(None),
    environment: str = Form(None),
    mac: str = Form(None),
    location: str = Form(None),
    description: str = Form(None),
    subnet_id: int = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        device_service.create_device(
            db, 
            hostname=hostname, 
            ip_addr=ip_addr, 
            status=status,
            device_type=device_type,
            environment=environment,
            mac=mac,
            location=location,
            description=description,
            created_by=user.username,
            subnet_id=subnet_id
        )
        resp = RedirectResponse(url="/devices", status_code=303)
        return flash(resp, "Uređaj je uspješno dodan u IPAM bazu!")
    except IntegrityError:
        # Greška ako IP ili Hostname već postoje
        subnets = db.query(subnet_service.Subnet).all()
        return templates.TemplateResponse("devices_add.html", {
            "request": request, "user": user, "subnets": subnets,
            "error": "Greška: Uređaj s tim Hostname-om ili IP adresom već postoji!"
        })
    except Exception as e:
        subnets = db.query(subnet_service.Subnet).all()
        return templates.TemplateResponse("devices_add.html", {
            "request": request, "user": user, "subnets": subnets,
            "error": f"Sustavna greška: {str(e)}"
        })

# --- PREGLED DETALJA ---
@router.get("/{device_id}")
def view_device(device_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    dev = device_service.get_device(db, device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Uređaj nije pronađen")
    return templates.TemplateResponse("devices_view.html", {
        "request": request, 
        "dev": dev,
        "user": user
    })

# --- UREĐIVANJE UREĐAJA ---
@router.get("/{device_id}/edit")
def edit_device_form(device_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    dev = device_service.get_device(db, device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Uređaj nije pronađen")
    
    subnets = db.query(subnet_service.Subnet).all()
    return templates.TemplateResponse("devices_edit.html", {
        "request": request, 
        "dev": dev, 
        "user": user,
        "subnets": subnets
    })

@router.post("/{device_id}/edit")
def update_device(
    device_id: int,
    request: Request,
    hostname: str = Form(...),
    ip_addr: str = Form(...),
    status: str = Form(...),
    device_type: str = Form(None),
    environment: str = Form(None),
    mac: str = Form(None),
    location: str = Form(None),
    description: str = Form(None),
    subnet_id: int = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        device_service.update_device(
            db, 
            device_id=device_id, 
            hostname=hostname, 
            ip_addr=ip_addr, 
            status=status,
            device_type=device_type,
            environment=environment,
            mac=mac,
            location=location,
            description=description,
            updated_by=user.username,
            subnet_id=subnet_id
        )
        resp = RedirectResponse(url=f"/devices/{device_id}", status_code=303)
        return flash(resp, "Promjene na uređaju su uspješno spremljene!")
    except Exception as e:
        dev = device_service.get_device(db, device_id)
        subnets = db.query(subnet_service.Subnet).all()
        return templates.TemplateResponse("devices_edit.html", {
            "request": request, "dev": dev, "user": user, "subnets": subnets,
            "error": f"Neuspješno ažuriranje: {str(e)}"
        })

# --- BRISANJE UREĐAJA ---
@router.post("/{device_id}/delete")
def delete_device(device_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    device_service.delete_device(db, device_id)
    resp = RedirectResponse(url="/devices", status_code=303)
    return flash(resp, "Uređaj je trajno uklonjen iz sustava.")

# --- LIVE PING ---
@router.post("/{device_id}/ping")
def run_ping(device_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Ova ruta vraća JSON koji AJAX u devices_list.html koristi za ažuriranje statusa
    result = device_service.ping_device(db, device_id)
    if not result:
        raise HTTPException(status_code=404, detail="Uređaj nije pronađen")
    return result