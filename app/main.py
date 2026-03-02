# v1.1.13
# Glavna ulazna točka aplikacije - IPAM sustav.
# Sadrži konfiguraciju ruta, statičkih datoteka i logiku za početnu analitičku ploču.

from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func

# Uvoz lokalnih modula
from app.api import auth, devices, subnets
from app.api.dependencies import get_current_user, get_db
from app.core.models import User, Device, Subnet
from app.core.ui import templates

app = FastAPI(title="IPAM System")

# Montiranje statičkih resursa (CSS, JS, Slike)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/scripts", StaticFiles(directory="app/scripts"), name="scripts")

# Uključivanje API routera s pripadajućim prefiksima
app.include_router(auth.router, prefix="/auth")
app.include_router(devices.router, prefix="/devices")
app.include_router(subnets.router, prefix="/subnets")

@app.get("/")
def home(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Početna stranica (Dashboard) koja prikuplja statistiku za vizualizaciju u realnom vremenu.
    """
    
    # 1. Osnovni brojači za info-kartice
    device_count = db.query(Device).count()
    subnet_count = db.query(Subnet).count()
    
    # 2. Statistika statusa (za Pie/Doughnut Chart na sučelju)
    # Grupiramo uređaje prema statusu i brojimo pojavljivanja
    status_stats = db.query(Device.status, func.count(Device.id)).group_by(Device.status).all()
    status_data = {s.value: count for s, count in status_stats}
    
    # 3. Statistika okruženja (za Bar Chart na sučelju)
    # Ako okruženje nije definirano, označavamo ga kao 'Unknown'
    env_stats = db.query(Device.environment, func.count(Device.id)).group_by(Device.environment).all()
    env_data = {env if env else "Unknown": count for env, count in env_stats}
    
    # Slanje svih podataka u home.html predložak
    return templates.TemplateResponse("home.html", {
        "request": request, 
        "user": user,
        "device_count": device_count,
        "subnet_count": subnet_count,
        "status_data": status_data,
        "env_data": env_data,
        "title": "Dashboard"
    })

# Napomena: Za pokretanje u produkciji koristite uvicorn:
# uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload