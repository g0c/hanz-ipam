# v1.1.53
# Authentication router. Koristi LDAPS s failoverom i centralizirane postavke iz config.py.

from fastapi import APIRouter, Depends, HTTPException, Response, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import ssl
from ldap3 import Server, Connection, ALL, Tls, ServerPool, ROUND_ROBIN

from app.core.config import settings
from app.core.models import User
from app.core.security import verify_password, create_access_token
from app.api.dependencies import get_db
from app.core.ui import templates

router = APIRouter()

def authenticate_via_ad(username, password):
    """
    LDAPS autentifikacija koristeći varijable iz settings objekta.
    """
    # Provjera jesu li sve potrebne AD postavke učitane
    if not all([settings.AD_SERVER, settings.AD_DOMAIN, settings.AD_BIND_USER]):
        print("Kritična greška: AD postavke nisu učitane iz .env datoteke!")
        return False, None

    try:
        tls_config = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
        
        # Razdvajamo string s IP adresama (npr. "10.2.2.114, 10.2.2.115")
        server_addresses = [addr.strip() for addr in settings.AD_SERVER.split(',')]
        
        # Kreiramo listu servera s portom 636 i SSL-om
        servers = [
            Server(addr, port=636, use_ssl=True, tls=tls_config, get_info=ALL, connect_timeout=3) 
            for addr in server_addresses
        ]
        
        # Pool omogućuje failover ako je jedan DC ugašen
        pool = ServerPool(servers, ROUND_ROBIN, active=True, exhaust=True)
        
        # 1. Spajanje sa service accountom (Bind)
        conn = Connection(pool, user=settings.AD_BIND_USER, password=settings.AD_BIND_PASS, auto_bind=True)
        
        # 2. Pretraga korisnika po sAMAccountName (username)
        search_filter = f"(&(objectClass=user)(sAMAccountName={username}))"
        conn.search(settings.AD_BASE_DN, search_filter, attributes=['displayName'])
        
        if not conn.entries:
            print(f"Korisnik {username} nije pronađen u AD-u.")
            return False, None
            
        user_dn = conn.entries[0].entry_dn
        display_name = str(conn.entries[0].displayName) if 'displayName' in conn.entries[0] else username
        
        # 3. Provjera korisničke lozinke pokušajem novog binda
        user_conn = Connection(pool, user=user_dn, password=password)
        if user_conn.bind():
            return True, {"username": username, "full_name": display_name}
            
        return False, None
    except Exception as e:
        print(f"LDAPS Greška prilikom prijave: {str(e)}")
        return False, None

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...)
):
    # Prvo tražimo korisnika u lokalnoj bazi podataka
    user = db.query(User).filter(User.username == username).first()
    auth_success = False
    
    # 1. POKUŠAJ: Lokalna autentifikacija (za admina ili lokalne usere)
    if user and user.hashed_password:
        if verify_password(password, user.hashed_password):
            auth_success = True

    # 2. POKUŠAJ: Ako lokalna nije uspjela, pokušaj Active Directory
    if not auth_success:
        ad_ok, ad_data = authenticate_via_ad(username, password)
        if ad_ok:
            auth_success = True
            # Just-In-Time kreiranje korisnika u bazi ako ne postoji
            if not user:
                user = User(
                    username=username,
                    full_name=ad_data["full_name"],
                    is_active=True,
                    hashed_password=None # AD korisnici nemaju lokalnu lozinku
                )
                db.add(user)
                db.commit()
                db.refresh(user)

    # Ako nijedna metoda nije uspjela
    if not auth_success or (user and not user.is_active):
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Neispravno korisničko ime ili lozinka"
        })

    # Generiranje tokena (koristimo postavke iz config.py)
    access_token = create_access_token(data={"uid": user.id})
    
    redirect = RedirectResponse(url="/dashboard", status_code=303)
    redirect.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return redirect

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response