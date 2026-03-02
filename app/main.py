# v1.1.12
from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api import auth, devices, subnets
from app.api.dependencies import get_current_user, get_db
from app.core.models import User, Device, Subnet
from app.core.ui import templates  # Uvoz centralnog objekta

app = FastAPI(title="IPAM")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/scripts", StaticFiles(directory="app/scripts"), name="scripts")

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