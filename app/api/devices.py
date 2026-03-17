# v1.1.27
# Kompletni ruter za uređaje. Sadrži "bulletproof" endpoint za IP detalje.

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_current_user, get_db
from app.services import device_service, subnet_service
from app.services.flash import flash
from app.core.ui import templates
from app.core.models import Device

router = APIRouter(tags=["devices"])

# KOMENTAR: Dohvaćanje detalja putem IP adrese (Uvijek vraća 200 OK za stabilnost frontenda)
@router.get("/details/{ip_addr}")
def get_device_details_by_ip(ip_addr: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        clean_ip = ip_addr.strip()
        device = db.query(Device).filter(Device.ip_addr == clean_ip).first()
        
        if not device:
            return JSONResponse(content={"exists": False, "ip": clean_ip})
        
        # Sigurno dohvaćanje statusa
        status_val = "unknown"
        if device.status:
            status_val = device.status.value if hasattr(device.status, 'value') else str(device.status)

        # Sigurno formatiranje datuma zadnjeg viđenja
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

@router.get("/")
def list_devices(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    devices = device_service.get_all_devices(db)
    return templates.TemplateResponse("devices_list.html", {
        "request": request, 
        "devices": devices,
        "user": user
    })

@router.get("/add")
def add_device_form(request: Request, ip: str = None, subnet_id: int = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    subnets = db.query(subnet_service.Subnet).all()
    return templates.TemplateResponse("devices_add.html", {
        "request": request,
        "user": user,
        "prefilled_ip": ip,
        "prefilled_subnet": subnet_id,
        "subnets": subnets
    })

# v1.1.29
# Popravljena redirekcija: Vraća korisnika na grid ako je uređaj dodan od tamo.

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
            return flash(resp, f"IP {ip_addr} već postoji u bazi! Preusmjereni ste na uređivanje.")

        # 2. Kreiranje novog uređaja preko servisa
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
        
        # KOMENTAR: Pametna redirekcija - ako imamo subnet_id, vrati nas na taj Grid
        if subnet_id:
            resp = RedirectResponse(url=f"/subnets/{subnet_id}", status_code=303)
            message = f"Uređaj {hostname} je uspješno dodan u mrežu."
        else:
            resp = RedirectResponse(url="/devices", status_code=303)
            message = "Uređaj je uspješno dodan u IPAM bazu!"

        return flash(resp, message)

    except Exception as e:
        db.rollback()
        # U slučaju greške, vraćamo formu s popisom podmreža
        from app.services import subnet_service
        subnets = db.query(subnet_service.Subnet).all()
        return templates.TemplateResponse("devices_add.html", {
            "request": request, 
            "user": user, 
            "error": f"Greška prilikom spremanja: {str(e)}", 
            "subnets": subnets
        })

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

@router.post("/{device_id}/edit")
def update_device(device_id: int, request: Request, hostname: str = Form(...), ip_addr: str = Form(...), status: str = Form(...), 
                  db: Session = Depends(get_db), user=Depends(get_current_user), **kwargs):
    try:
        device_service.update_device(db, device_id=device_id, hostname=hostname, ip_addr=ip_addr, status=status, updated_by=user.username)
        resp = RedirectResponse(url=f"/devices/{device_id}", status_code=303)
        return flash(resp, "Spremljeno!")
    except Exception as e:
        db.rollback()
        return flash(RedirectResponse(url=f"/devices/{device_id}/edit", status_code=303), f"Greška: {str(e)}")

@router.post("/{device_id}/delete")
def delete_device(device_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    device_service.delete_device(db, device_id)
    return flash(RedirectResponse(url="/devices", status_code=303), "Obrisano.")