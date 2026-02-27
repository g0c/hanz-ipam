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

@router.get("/")
def list_devices(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Vraćamo SVE zapise — DataTables radi paginaciju/sort/search u browseru
    devices = device_service.get_all_devices(db)
    return templates.TemplateResponse("devices_list.html", {
        "request": request,
        "devices": devices
    })

@router.get("/add")
def add_device_form(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("devices_add.html", {"request": request})

@router.post("/add")
def add_device(
    request: Request,
    hostname: str = Form(...),
    ip_addr: str = Form(...),
    status: str = Form("unknown"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        device_service.create_device(db, hostname, ip_addr, status)
    except ValueError:
        return templates.TemplateResponse("devices_add.html", {
            "request": request,
            "error": "Neispravna IP adresa."
        })
    except IntegrityError:
        return templates.TemplateResponse("devices_add.html", {
            "request": request,
            "error": "IP adresa već postoji u bazi."
        })

    resp = RedirectResponse(url="/devices", status_code=303)
    # ASCII poruka zbog cookie header ograničenja
    return flash(resp, "Uredaj uspjesno dodan!")

@router.get("/{device_id}")
def view_device(device_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    dev = device_service.get_device(db, device_id)
    if not dev:
        raise HTTPException(404)
    return templates.TemplateResponse("devices_view.html", {"request": request, "dev": dev})

@router.get("/{device_id}/edit")
def edit_device_form(device_id: int, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    dev = device_service.get_device(db, device_id)
    if not dev:
        raise HTTPException(404)
    return templates.TemplateResponse("devices_edit.html", {"request": request, "dev": dev})

@router.post("/{device_id}/edit")
def edit_device(
    request: Request,
    device_id: int,
    hostname: str = Form(...),
    ip_addr: str = Form(...),
    status: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        device_service.update_device(db, device_id, hostname, ip_addr, status)
    except ValueError:
        return templates.TemplateResponse("devices_edit.html", {
            "request": request,
            "dev": device_service.get_device(db, device_id),
            "error": "Neispravna IP adresa."
        })
    except IntegrityError:
        return templates.TemplateResponse("devices_edit.html", {
            "request": request,
            "dev": device_service.get_device(db, device_id),
            "error": "Duplikat IP adrese."
        })

    resp = RedirectResponse(url=f"/devices/{device_id}", status_code=303)
    return flash(resp, "Uredaj uspjesno azuriran!")

@router.post("/{device_id}/delete")
def delete_device(device_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    device_service.delete_device(db, device_id)
    resp = RedirectResponse(url="/devices", status_code=303)
    return flash(resp, "Uredaj obrisan.")