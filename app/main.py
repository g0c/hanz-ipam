from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import auth
from app.api.dependencies import get_current_user
from app.core.models import User

app = FastAPI(title="IPAM")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router, prefix="/auth")

@app.get("/")
def home(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("home.html", {"request": request, "user": user})