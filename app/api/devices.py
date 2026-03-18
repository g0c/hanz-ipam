# v1.1.37
# Ruter za uređaje - Fixed: Uklonjen **kwargs koji je uzrokovao validation error.
# Sva polja forme su sada eksplicitno navedena.

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.api.dependencies import get_current_user, get_db
from app.services import device_service, subnet_service
from app.services.flash import flash
from app.core.ui import templates
from app.core.models import Device

router = APIRouter(tags=["devices"])

# --- DOHVAĆANJE DETALJA (Za IP Mapu) ---
@router.get("/details/{ip_addr}")
def get_device_details_by_ip(ip_addr: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        clean_ip = ip_addr.strip()
        device = db.query(Device).filter(Device.ip_addr == clean_ip).first()
        
        if not device:
            return JSONResponse(content={"exists": False, "ip": clean_ip})
        
        status_val = "unknown"
        if device.status:
            status_val = device.status.value if hasattr(device.status, 'value') else str(device.status)

        ls_str = "Nikada"
        if hasattr(device, 'last_seen') and device.last_seen:
            ls_str = device.last_seen.strftime("%d.%m.%Y %H:%M")

        return {
            "exists": True,
            "id": device.id,
            "ip": device.ip_addr,
            "hostname": device.hostname or "Nema imena",
            "status": status_val,
            "mac_address": getattr(device, 'mac', 'Nepoznato') or "Nepoznato",
            "last_seen": ls_str
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"exists": False, "error": str(e)})

# --- LISTA UREĐAJA ---
@router.get("/")
def list_devices(request: Request, status: Optional[str] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(Device)
    if status:
        query = query.filter(Device.status == status)
    devices = query.all()
    return templates.TemplateResponse("devices_list.html", {"request": request, "devices": devices, "user": user, "active_filter": status})

# --- DODAVANJE UREĐAJA ---
@router.post("/add")
def add_device(
    request: Request,
    hostname: str = Form(...),
    ip_addr: str = Form(...),
    status: str = Form("unknown"),
    device_type: Optional[str] = Form(None),
    environment: Optional[str] = Form(None),
    mac: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    subnet_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        existing = db.query(Device).filter(Device.ip_addr == ip_addr).first()
        if existing:
            return flash(RedirectResponse(url=f"/devices/{existing.id}/edit", status_code=303), f"IP {ip_addr} već postoji!")

        device_service.create_device(
            db, hostname=hostname, ip_addr=ip_addr, status=status,
            device_type=device_type, environment=environment, mac=mac,
            location=location, description=description, 
            created_by=user.username, subnet_id=subnet_id
        )
        
        url = f"/subnets/{subnet_id}" if subnet_id else "/devices"
        return flash(RedirectResponse(url=url, status_code=303), "Uređaj dodan!")
    except Exception as e:
        db.rollback()
        subnets = db.query(subnet_service.Subnet).all()
        return templates.TemplateResponse("devices_add.html", {"request": request, "user": user, "error": str(e), "subnets": subnets})

# --- UREĐIVANJE UREĐAJA (Ovdje je bio bug) ---
@router.post("/{device_id}/edit")
def update_device(
    device_id: int,
    request: Request,
    hostname: str = Form(...),
    ip_addr: str = Form(...),
    status: str = Form(...),
    device_type: Optional[str] = Form(None),
    environment: Optional[str] = Form(None),
    mac: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    subnet_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        # KOMENTAR: Eksplicitno prosljeđujemo sva polja servisu
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
        return flash(RedirectResponse(url=f"/devices/{device_id}/edit", status_code=303), f"Greška: {str(e)}")

# --- OSTALE RUTE ---
@router.get("/{device_id}")
def view_device(device_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    dev = device_service.get_device(db, device_id)
    if not dev: raise HTTPException(status_code=404)
    return templates.TemplateResponse("devices_view.html", {"request": request, "dev": dev, "user": user})

@router.get("/{device_id}/edit")
def edit_device_form(device_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    dev = device_service.get_device(db, device_id)
    if not dev: raise HTTPException(status_code=404)
    subnets = db.query(subnet_service.Subnet).all()
    return templates.TemplateResponse("devices_edit.html", {"request": request, "dev": dev, "user": user, "subnets": subnets})

@router.post("/{device_id}/delete")
def delete_device(device_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    device_service.delete_device(db, device_id)
    return flash(RedirectResponse(url="/devices", status_code=303), "Uređaj obrisan.")