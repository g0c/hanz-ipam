# v1.0.0
# Ruter za pregled povijesti aktivnosti i reviziju sustava (Audit Log).

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, get_db
from app.core.models import AuditLog, User
from app.core.ui import templates

router = APIRouter(tags=["audit"])

@router.get("/")
def list_audit_logs(
    request: Request, 
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    """
    Prikazuje listu svih zabilježenih događaja u sustavu, 
    poredanih od najnovijih prema starijima.
    """
    # Dohvaćamo sve logove sortirane po vremenu (timestamp desc)
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    
    return templates.TemplateResponse("audit_list.html", {
        "request": request,
        "user": user,
        "logs": logs,
        "title": "Audit Logs"
    })