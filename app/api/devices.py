# v1.1.20
# Ruter za upravljanje mrežnim uređajima - IPAM modul.
# Dodana podrška za dohvaćanje detalja putem IP adrese za interaktivnu mapu.

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_current_user, get_db
from app.services import device_service, subnet_service
from app.services.flash import flash
from app.core.ui import templates
from app.core.models import Device

router = APIRouter(tags=["devices"])

# --- DOHVAĆANJE DETALJA PREKO IP ADRESE (Za Modal na IP Mapi) ---
# Ova ruta omogućuje interaktivnoj mapi da povuče podatke čim klikneš na kockicu.
@router.get("/details/{ip_addr}")
def get_device_details_by_ip(ip_addr: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Traženje uređaja u bazi prema IP adresi
    device = db.query(Device).filter(Device.ip_addr == ip_addr).first()
    
    if not device:
        # Ako uređaj ne postoji u bazi, vraćamo 404 što JS hvata i prikazuje "Free IP"
        raise HTTPException(status_code=404, detail="Uređaj nije pronađen")
    
    # Vraćanje JSON podataka koje JavaScript očekuje za popunjavanje modala
    return {
        "id": device.id,
        "ip": device.ip_addr,
        "hostname": device.hostname,
        "status": device.status.value if hasattr(device.status, 'value') else str(device.status),
        "mac_address": device.mac_address,
        "last_seen": device.last_seen.strftime("%Y-%m-%d %H:%M:%S") if device.last_seen else "Never"
    }

# --- LISTA UREĐAJA ---
@router.get("/")
def list_devices(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Dohvaćanje svih uređaja za tablični prikaz
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
    # Forma za dodavanje - prima prefilled podatke iz IP mape
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
        # 1. Provjera postoji li već uređaj s ovom IP adresom
        existing = db.query(Device).filter(Device.ip_addr == ip_addr).first()
        if existing:
            resp = RedirectResponse(url=f"/devices/{existing.id}/edit", status_code=303)
            return flash(resp, f"Uređaj s IP adresom {ip_addr} već postoji u bazi! Preusmjereni ste na uređivanje.")

        # 2. Ako IP ne postoji, kreiraj novi zapis
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

    except Exception as e:
        db.rollback()
        subnets = db.query(subnet_service.Subnet).all()
        return templates.TemplateResponse("devices_add.html", {
            "request": request, 
            "user": user, 
            "error": f"Greška prilikom spremanja: {str(e)}", 
            "subnets": subnets
        })

# --- PREGLED DETALJA (Po ID-u) ---
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
        return flash(resp, "Promjene su uspješno spremljene!")
    except Exception as e:
        db.rollback()
        dev = device_service.get_device(db, device_id)
        subnets = db.query(subnet_service.Subnet).all()
        return templates.TemplateResponse("devices_edit.html", {
            "request": request, 
            "dev": dev, 
            "user": user,
            "error": f"Greška pri ažuriranju: {str(e)}",
            "subnets": subnets
        })

# --- BRISANJE UREĐAJA ---
@router.post("/{device_id}/delete")
def delete_device(device_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        device_service.delete_device(db, device_id)
        resp = RedirectResponse(url="/devices", status_code=303)
        return flash(resp, "Uređaj je trajno uklonjen iz IPAM sustava.")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Greška pri brisanju uređaja.")

# --- LIVE PING ---
@router.post("/{device_id}/ping")
def run_ping(device_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    result = device_service.ping_device(db, device_id)
    if not result:
        raise HTTPException(status_code=404, detail="Uređaj nije pronađen")
    return result