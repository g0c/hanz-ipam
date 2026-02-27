# v1.0.2
from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import auth
from app.api import devices  # Dodano učitavanje routera za uređaje
from app.api.dependencies import get_current_user
from app.core.models import User

app = FastAPI(title="IPAM")

# Povezivanje statičkih datoteka i Jinja2 predložaka
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Registracija svih ruta u aplikaciji
app.include_router(auth.router, prefix="/auth")
app.include_router(devices.router, prefix="/devices")  # Povezivanje ruta za pregled i uređivanje uređaja

# Početna stranica nadzorne ploče (zahtijeva prijavu)
@app.get("/")
def home(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("home.html", {"request": request, "user": user})