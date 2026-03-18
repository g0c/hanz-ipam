# v1.1.59
# Glavna datoteka aplikacije. 
# Popravljen redoslijed inicijalizacije (Fix: NameError).
# Integriran Backup Monitor i CheckIPAM Lite Monitor.

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import subprocess
import os
import glob
import time
from datetime import datetime

# Importi za monitoring
from apscheduler.schedulers.background import BackgroundScheduler

# Uvozimo centralne postavke i routere
from app.core.config import settings
from app.api import auth, devices, subnets, audit, discovery_ws
from app.api.dependencies import get_current_user, get_db
from app.core.models import User, Device, Subnet
from app.core.ui import templates
from app.services.dns_sync import run_dns_sync
from app.services.monitor import run_monitor_lite  # Osiguraj da ovaj file postoji
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import jwt

# KOMENTAR: Putanja do backupa
BACKUP_DIR = "/home/su/projects/hanz-ipam/backups"

# --- POMOĆNE FUNKCIJE ---

def get_git_hash():
    try:
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
    except Exception:
        return "1.1.59"

def get_last_backup_status():
    try:
        files = glob.glob(os.path.join(BACKUP_DIR, "*.tar.gz"))
        if not files: return None
        last_file = max(files, key=os.path.getctime)
        stats = os.stat(last_file)
        return {
            "filename": os.path.basename(last_file),
            "time": datetime.fromtimestamp(stats.st_ctime).strftime("%d.%m.%Y. %H:%M"),
            "size_mb": round(stats.st_size / (1024 * 1024), 2),
            "is_recent": (time.time() - stats.st_ctime) < 90000 
        }
    except Exception:
        return None

# --- INICIJALIZACIJA APLIKACIJE ---

app = FastAPI(title=settings.APP_NAME)

# Postavljanje verzije za footer
templates.env.globals["app_version"] = get_git_hash()

# --- POZADINSKI MONITORING (APScheduler) ---

scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_monitoring():
    """Pokreće pozadinski monitor svake 2 minute."""
    def monitor_job():
        # Otvaramo novu sesiju baze za pozadinski task
        db_gen = get_db()
        db = next(db_gen)
        try:
            run_monitor_lite(db)
        finally:
            db_gen.close()

    scheduler.add_job(monitor_job, 'interval', minutes=2, id="checkipam_monitor")
    scheduler.start()

@app.on_event("shutdown")
def stop_monitoring():
    scheduler.shutdown()

# --- MIDDLEWARE I EXCEPTION HANDLERI ---

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/auth/login")
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STATIČKE DATOTEKE I RUTERE ---

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/scripts", StaticFiles(directory="app/scripts"), name="scripts")

app.include_router(auth.router, prefix="/auth")
app.include_router(devices.router, prefix="/devices")
app.include_router(subnets.router, prefix="/subnets")
app.include_router(audit.router, prefix="/audit")
app.include_router(discovery_ws.router)

# --- RUTE ---

@app.post("/api/sync-dns")
async def sync_dns_endpoint(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
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
        jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGO])
        return RedirectResponse(url="/dashboard")
    except Exception:
        return RedirectResponse(url="/auth/login")

# v1.1.60
# Dashboard ruter s podrškom za NOC status i asinkroni monitor.

@app.get("/dashboard")
async def dashboard_view(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.core.models import AuditLog
    
    count_subnets = db.query(Subnet).count()
    count_devices = db.query(Device).count()
    
    status_stats = db.query(Device.status, func.count(Device.id)).group_by(Device.status).all()
    status_data = {str(s[0].value if hasattr(s[0], 'value') else s[0]): s[1] for s in status_stats}

    env_stats = db.query(Device.environment, func.count(Device.id)).group_by(Device.environment).all()
    env_data = {str(e[0] if e[0] else "Unknown"): e[1] for e in env_stats}

    # DOHVAĆANJE ZADNJIH INCIDENATA (OFFLINE/ONLINE promjene)
    recent_logs = db.query(AuditLog).filter(
        AuditLog.action.in_(["STATUS_CHANGE", "DISCOVERY"])
    ).order_by(AuditLog.timestamp.desc()).limit(7).all()

    # IZRČUN KAPACITETA (Procjena na temelju /24 subneta)
    total_capacity = count_subnets * 254 if count_subnets > 0 else 1
    usage_percentage = round((count_devices / total_capacity) * 100, 1)

    return templates.TemplateResponse("home.html", {
        "request": request, "user": user, "device_count": count_devices,
        "subnet_count": count_subnets, "status_data": status_data,
        "env_data": env_data, "backup_info": get_last_backup_status(),
        "recent_logs": recent_logs, "usage_percentage": usage_percentage
    })