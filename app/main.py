# v1.1.54
# Glavna datoteka aplikacije. Centralizirano upravljanje postavkama.

from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi import BackgroundTasks # Za pokretanje u pozadini ako je zona velika
from app.services.dns_sync import run_dns_sync
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import jwt

# Uvozimo centralne postavke i routere
from app.core.config import settings
from app.api import auth, devices, subnets, audit, discovery_ws
from app.api.dependencies import get_current_user, get_db
from app.core.models import User, Device, Subnet
from app.core.ui import templates

# Inicijalizacija aplikacije s nazivom iz config.py
app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/scripts", StaticFiles(directory="app/scripts"), name="scripts")

app.include_router(auth.router, prefix="/auth")
app.include_router(devices.router, prefix="/devices")
app.include_router(subnets.router, prefix="/subnets")
app.include_router(audit.router, prefix="/audit")
app.include_router(discovery_ws.router)

# KOMENTAR: Ruta koja pokreće sinkronizaciju i vraća broj obrađenih uređaja
@app.post("/api/sync-dns")
async def sync_dns_endpoint(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Pokreće DNS sinkronizaciju. Zaštićeno dependencyjem za trenutnog korisnika.
    """
    try:
        count = run_dns_sync(db)
        return {"status": "success", "message": f"Synced {count} devices from DNS."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/auth/login")
    try:
        # Dekodiranje koristeći ključeve iz settings
        jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGO])
        return RedirectResponse(url="/dashboard")
    except Exception:
        return RedirectResponse(url="/auth/login")

@app.get("/dashboard")
async def dashboard_view(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    count_subnets = db.query(Subnet).count()
    count_devices = db.query(Device).count()
    
    status_stats = db.query(Device.status, func.count(Device.id)).group_by(Device.status).all()
    status_data = {str(s[0].value if hasattr(s[0], 'value') else s[0]): s[1] for s in status_stats}

    env_stats = db.query(Device.environment, func.count(Device.id)).group_by(Device.environment).all()
    env_data = {str(e[0] if e[0] else "Unknown"): e[1] for e in env_stats}

    return templates.TemplateResponse("home.html", {
        "request": request,
        "user": user,
        "title": f"{settings.APP_NAME} DASHBOARD",
        "subnet_count": count_subnets,
        "device_count": count_devices,
        "status_data": status_data,
        "env_data": env_data
    })