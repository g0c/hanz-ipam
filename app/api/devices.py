# v1.1.39
# Ruter za uređaje - Ispravljen problem s validacijom forme (422 Unprocessable Entity)

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Annotated # Dodano Annotated za bolju validaciju

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
    return templates.TemplateResponse(request=request, name="devices_list.html", context={"devices": devices, "user": user, "active_filter": status})


# --- PRIKAZ FORME ZA DODAVANJE UREĐAJA (OVO JE FALILO) ---
@router.get("/add")
def add_device_form(
    request: Request, 
    ip: Optional[str] = None, 
    subnet_id: Optional[int] = None, 
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    # Komentar: Dohvaćamo podmreže za dropdown izbornik i prosljeđujemo IP da se forma unaprijed popuni
    subnets = db.query(subnet_service.Subnet).all()
    return templates.TemplateResponse(request=request, name="devices_add.html", context={"user": user, 
        "subnets": subnets,
        "prefill_ip": ip,
        "prefill_subnet": subnet_id})


# --- DODAVANJE UREĐAJA U BAZU ---
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
        return templates.TemplateResponse(request=request, name="devices_add.html", context={"user": user, "error": str(e), "subnets": subnets})

# --- UREĐIVANJE UREĐAJA (POST) ---
# Ova ruta prima podatke iz HTML forme i ažurira bazu
@router.post("/{device_id}/edit")
def update_device(
    device_id: int,
    request: Request,
    # Primamo kao Optional[str] da izbjegnemo Pydantic 422 grešku ako je polje prazno
    hostname: Annotated[Optional[str], Form()] = None,
    ip_addr: Annotated[Optional[str], Form()] = None,
    status: Annotated[Optional[str], Form()] = "unknown",
    device_type: Annotated[Optional[str], Form()] = None,
    environment: Annotated[Optional[str], Form()] = None,
    mac: Annotated[Optional[str], Form()] = None,
    location: Annotated[Optional[str], Form()] = None,
    description: Annotated[Optional[str], Form()] = None,
    subnet_id: Annotated[Optional[str], Form()] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    try:
        # 1. Validacija: Hostname i IP ne smiju biti stvarno None ili samo razmaci
        if not hostname or not hostname.strip():
            # Ako je prazno, možemo vratiti grešku ili staviti fallback
            return flash(RedirectResponse(url=f"/devices/{device_id}/edit", status_code=303), "Greška: Hostname je obavezan!")
        
        if not ip_addr or not ip_addr.strip():
            return flash(RedirectResponse(url=f"/devices/{device_id}/edit", status_code=303), "Greška: IP adresa je obavezna!")

        # 2. Čišćenje podataka (Empty String -> None)
        clean_subnet_id = int(subnet_id) if subnet_id and subnet_id.strip() else None
        clean_mac = mac.strip() if mac and mac.strip() else None
        
        # 3. Poziv servisa
        device_service.update_device(
            db, 
            device_id=device_id, 
            hostname=hostname.strip(), 
            ip_addr=ip_addr.strip(), 
            status=status,
            device_type=device_type,
            environment=environment,
            mac=clean_mac,
            location=location,
            description=description,
            updated_by=user.username,
            subnet_id=clean_subnet_id
        )
        
        resp = RedirectResponse(url=f"/devices/{device_id}", status_code=303)
        return flash(resp, "Uređaj uspješno ažuriran!")
        
    except Exception as e:
        db.rollback()
        return flash(RedirectResponse(url=f"/devices/{device_id}/edit", status_code=303), f"Sustavna greška: {str(e)}")




# --- OSTALE RUTE ---
@router.get("/{device_id}")
def view_device(device_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    dev = device_service.get_device(db, device_id)
    if not dev: raise HTTPException(status_code=404)
    return templates.TemplateResponse(request=request, name="devices_view.html", context={"dev": dev, "user": user})

@router.get("/{device_id}/edit")
def edit_device_form(device_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    dev = device_service.get_device(db, device_id)
    if not dev: raise HTTPException(status_code=404)
    subnets = db.query(subnet_service.Subnet).all()
    return templates.TemplateResponse(request=request, name="devices_edit.html", context={"dev": dev, "user": user, "subnets": subnets})

@router.post("/{device_id}/delete")
def delete_device(device_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    device_service.delete_device(db, device_id)
    return flash(RedirectResponse(url="/devices", status_code=303), "Uređaj obrisan.")