# v1.1.16
# Glavna datoteka koja inicijalizira FastAPI aplikaciju, rute i CORS postavke.

from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api import auth, devices, subnets, audit, discovery_ws
from app.api.dependencies import get_current_user, get_db
from app.core.models import User, Device, Subnet
from app.core.ui import templates

# Inicijalizacija glavnog FastAPI objekta i osnovnih postavki.
app = FastAPI(title="IPAM System")

# Konfiguracija CORS-a za ispravan rad WebSocket veze i vanjskih HTTP zahtjeva.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Povezivanje statičkih datoteka (CSS, JS) s aplikacijom kako bi ih frontend mogao učitati.
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/scripts", StaticFiles(directory="app/scripts"), name="scripts")

# Uključivanje svih API ruta u glavnu aplikaciju za obradu zahtjeva.
app.include_router(auth.router, prefix="/auth")
app.include_router(devices.router, prefix="/devices")
app.include_router(subnets.router, prefix="/subnets")
app.include_router(audit.router, prefix="/audit")
app.include_router(discovery_ws.router)

# Ruta za prikaz glavne nadzorne ploče (Dashboard).
# Dohvaća statistiku iz baze podataka (broj uređaja, podmreža i statuse) za Jinja2 predložak.
@app.get("/")
def home(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    
    # Dohvaćanje ukupnog broja instanci za podmreže i uređaje iz baze.
    GOC1_subnet_count = db.query(Subnet).count()
    GOC1_device_count = db.query(Device).count()
    
    # Grupiranje uređaja prema njihovom trenutnom statusu radi prikaza statistike na sučelju.
    GOC1_status_query = db.query(Device.status, func.count(Device.id)).group_by(Device.status).all()
    
    # Generiranje rječnika sa statusima za ispravno parsiranje u HTML predlošku.
    status_data = {}
    for row in GOC1_status_query:
        status_obj, count = row
        status_key = status_obj.value if hasattr(status_obj, 'value') else str(status_obj)
        status_data[status_key] = count

    return templates.TemplateResponse("home.html", {
        "request": request,
        "user": user,
        "title": "GLOBAL OPERATIONS CENTER ONE",
        "subnet_count": GOC1_subnet_count,
        "device_count": GOC1_device_count,
        "status_data": status_data
    })