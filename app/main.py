# v1.1.9
# Glavna datoteka aplikacije - rješava rute, statiku i početni prikaz.

import urllib.parse
from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api import auth, devices, subnets
from app.api.dependencies import get_current_user, get_db
from app.core.models import User, Device, Subnet

app = FastAPI(title="IPAM")

# Montiranje statičkih datoteka iz app foldera
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/scripts", StaticFiles(directory="app/scripts"), name="scripts")

templates = Jinja2Templates(directory="app/templates")

# Funkcija za čitanje i dekodiranje flash poruka (pretvara %C5%A1 natrag u 'š')
def get_flash_message(request: Request):
    flash = request.cookies.get("flash")
    return urllib.parse.unquote(flash) if flash else None

# Registracija globalne funkcije kako bi bila dostupna u svim Jinja2 predlošcima
templates.env.globals["get_flash"] = get_flash_message

# Registracija svih routera
app.include_router(auth.router, prefix="/auth")
app.include_router(devices.router, prefix="/devices")
app.include_router(subnets.router, prefix="/subnets")

# Početna stranica nadzorne ploče s brojačima
@app.get("/")
def home(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Dohvaćanje statistike za dashboard
    device_count = db.query(Device).count()
    subnet_count = db.query(Subnet).count()
    
    return templates.TemplateResponse("home.html", {
        "request": request, 
        "user": user,
        "device_count": device_count,
        "subnet_count": subnet_count
    })