# v1.1.55
# Authentication router. Koristi LDAPS, bilježi login događaje s ispravnim IP-om i vrši audit.

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
from app.services import audit_service # Uvoz audit servisa

router = APIRouter(tags=["auth"])

# KOMENTAR: LDAPS autentifikacija koristeći varijable iz settings objekta
def authenticate_via_ad(username, password):
    if not all([settings.AD_SERVER, settings.AD_DOMAIN, settings.AD_BIND_USER]):
        print("Kritična greška: AD postavke nisu učitane!")
        return False, None

    try:
        tls_config = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
        server_list = [addr.strip() for addr in settings.AD_SERVER.split(',')]
        
        servers = [
            Server(addr, port=636, use_ssl=True, tls=tls_config, get_info=ALL, connect_timeout=3) 
            for addr in server_list
        ]
        
        pool = ServerPool(servers, ROUND_ROBIN, active=True, exhaust=True)
        
        try:
            conn = Connection(pool, user=settings.AD_BIND_USER, password=settings.AD_BIND_PASS, auto_bind=True)
        except Exception as bind_err:
            print(f"Kritično: BIND nije uspio. Greška: {bind_err}")
            return False, None
            
        search_filter = f"(&(objectClass=user)(sAMAccountName={username}))"
        conn.search(settings.AD_BASE_DN, search_filter, attributes=['displayName'])
        
        if not conn.entries:
            conn.unbind()
            return False, None
            
        user_dn = conn.entries[0].entry_dn
        try:
            display_name = str(conn.entries[0].displayName)
        except AttributeError:
            display_name = username
            
        user_conn = Connection(pool, user=user_dn, password=password)
        if user_conn.bind():
            user_conn.unbind()
            conn.unbind()
            return True, {"username": username, "full_name": display_name}
            
        conn.unbind()
        return False, None
        
    except Exception as e:
        print(f"Neočekivana LDAPS greška: {str(e)}")
        return False, None

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...)
):
    # KOMENTAR: Izvlačenje stvarne IP adrese korisnika (iza Apache proxyja)
    client_ip = request.headers.get("X-Real-IP") or request.client.host
    
    user = db.query(User).filter(User.username == username).first()
    auth_success = False
    
    # 1. POKUŠAJ: Lokalna autentifikacija
    if user and user.hashed_password:
        if verify_password(password, user.hashed_password):
            auth_success = True

    # 2. POKUŠAJ: Active Directory autentifikacija
    if not auth_success:
        ad_ok, ad_data = authenticate_via_ad(username, password)
        if ad_ok:
            auth_success = True
            if not user:
                # Kreiraj lokalni zapis za AD korisnika ako ne postoji
                user = User(
                    username=username,
                    full_name=ad_data["full_name"],
                    is_active=True,
                    hashed_password=None
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            elif not user.full_name:
                 user.full_name = ad_data["full_name"]
                 db.commit()

    # KOMENTAR: Ako prijava nije uspjela, bilježimo neuspješan pokušaj
    if not auth_success or (user and not user.is_active):
        audit_service.log_event(
            db, 
            username=username, 
            action="LOGIN_FAILED", 
            target_type="USER", 
            details="Neuspješan pokušaj prijave ili deaktiviran račun.",
            source_ip=client_ip
        )
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Neispravno korisničko ime ili lozinka"})

    # KOMENTAR: Bilježenje uspješne prijave u Audit Log s ispravnim IP-om
    audit_service.log_event(
        db, 
        username=user.username, 
        action="LOGIN", 
        target_type="USER", 
        target_id=user.id, 
        details=f"Korisnik se uspješno prijavio u sustav.",
        source_ip=client_ip
    )

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
async def logout(request: Request, db: Session = Depends(get_db)):
    # Ovdje bi se moglo dodati logiranje logouta ako je potrebno
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response