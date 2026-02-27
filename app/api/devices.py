# v1.0.2
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_current_user, get_db
from app.services import device_service
from app.services.flash import flash

router = APIRouter(tags=["devices"])
templates = Jinja2Templates(directory="app/templates")

# Prikazuje listu svih uređaja
@router.get("/")
def list_devices(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    devices = device_service.get_all_devices(db)
    return templates.TemplateResponse("devices_list.html", {"request": request, "devices": devices})

# Forma za dodavanje novog uređaja
@router.get("/add")
def add_device_form(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("devices_add.html", {"request": request})

# Obrada unosa novog uređaja s proširenim poljima (MAC, lokacija, opis)
@router.post("/add")
def add_device(
    request: Request,
    hostname: str = Form(...),
    ip_addr: str = Form(...),
    status: str = Form("unknown"),
    mac: str = Form(None),
    location: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        device_service.create_device(db, hostname, ip_addr, status, mac, location, description)
    except ValueError:
        return templates.TemplateResponse("devices_add.html", {"request": request, "error": "Neispravna IP adresa."})
    except IntegrityError:
        return templates.TemplateResponse("devices_add.html", {"request": request, "error": "IP adresa već postoji u bazi."})

    resp = RedirectResponse(url="/devices", status_code=303)
    return flash(resp, "Uredaj uspjesno dodan!")

# Prikaz detalja uređaja
@router.get("/{device_id}")
def view_device(device_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    dev = device_service.get_device(db, device_id)
    if not dev:
        raise HTTPException(404)
    return templates.TemplateResponse("devices_view.html", {"request": request, "dev": dev})

# Brisanje uređaja
@router.post("/{device_id}/delete")
def delete_device(device_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    device_service.delete_device(db, device_id)
    resp = RedirectResponse(url="/devices", status_code=303)
    return flash(resp, "Uredaj obrisan.")

# v1.0.3
@router.get("/{device_id}/edit")
def edit_device_form(device_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    dev = device_service.get_device(db, device_id)
    if not dev:
        raise HTTPException(404, detail="Uređaj nije pronađen")
    return templates.TemplateResponse("devices_edit.html", {"request": request, "dev": dev})

@router.post("/{device_id}/edit")
def update_device(
    device_id: int,
    request: Request,
    hostname: str = Form(...),
    ip_addr: str = Form(...),
    status: str = Form(...),
    mac: str = Form(None),
    location: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        device_service.update_device(db, device_id, hostname, ip_addr, status, mac, location, description)
    except Exception as e:
        dev = device_service.get_device(db, device_id)
        return templates.TemplateResponse("devices_edit.html", {"request": request, "dev": dev, "error": str(e)})

    resp = RedirectResponse(url=f"/devices/{device_id}", status_code=303)
    return flash(resp, "Promjene su uspješno spremljene!")