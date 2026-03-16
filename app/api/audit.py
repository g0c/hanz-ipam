# v1.1.28
# Ruter za Audit Log s ugrađenim automatskim čišćenjem zapisa starijih od 30 dana.

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, get_db
from app.core.models import AuditLog, User
from app.core.ui import templates
from datetime import datetime, timedelta

router = APIRouter(tags=["audit"])

# KOMENTAR: Dohvaća sve zapise i automatski čisti povijest stariju od 30 dana.
@router.get("/")
def list_audit_logs(
    request: Request, 
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    """
    Prikazuje listu svih događaja uz automatsko održavanje baze (brisanje starih logova).
    """
    
    # KOMENTAR: Automatsko čišćenje - brišemo sve starije od 30 dana
    granica_starosti = datetime.now() - timedelta(days=30)
    try:
        db.query(AuditLog).filter(AuditLog.timestamp < granica_starosti).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        # Logiramo grešku u konzolu ako čišćenje ne uspije
        print(f"Greška pri automatskom čišćenju audit logova: {e}")

    # KOMENTAR: Dohvaćanje preostalih zapisa (najnoviji prvi)
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    
    return templates.TemplateResponse("audit_list.html", {
        "request": request,
        "user": user,
        "logs": logs,
        "title": "Audit Logs"
    })