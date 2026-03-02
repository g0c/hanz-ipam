# v1.1.11
import urllib.parse
from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api import auth, devices, subnets
from app.api.dependencies import get_current_user, get_db
from app.core.models import User, Device, Subnet

app = FastAPI(title="IPAM")

# Montiranje statike
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/scripts", StaticFiles(directory="app/scripts"), name="scripts")

# Inicijalizacija i registracija filtera za hrvatska slova
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["unquote"] = urllib.parse.unquote

# Registracija ruter-a
app.include_router(auth.router, prefix="/auth")
app.include_router(devices.router, prefix="/devices")
app.include_router(subnets.router, prefix="/subnets")

@app.get("/")
def home(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    device_count = db.query(Device).count()
    subnet_count = db.query(Subnet).count()
    
    return templates.TemplateResponse("home.html", {
        "request": request, 
        "user": user,
        "device_count": device_count,
        "subnet_count": subnet_count
    })