# v1.0.2
# Audit Engine - Servis za trajno bilježenje aktivnosti i automatsko održavanje baze.

from sqlalchemy.orm import Session
from app.core.models import AuditLog
from datetime import datetime, timedelta

def log_event(db: Session, username: str, action: str, target_type: str, 
              target_id: int = None, details: str = None, source_ip: str = "127.0.0.1"):
    """
    Glavna funkcija za upisivanje događaja. 
    Zadana vrijednost za source_ip je 127.0.0.1 ako se ne proslijedi drugačije.
    """
    try:
        new_log = AuditLog(
            username=username,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            source_ip=source_ip
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Kritična greška u Audit servisu: {e}")

def cleanup_old_logs(db: Session, days: int = 30):
    """
    KOMENTAR: Automatsko čišćenje zapisa starijih od zadanog broja dana.
    """
    try:
        granica = datetime.now() - timedelta(days=days)
        deleted_count = db.query(AuditLog).filter(AuditLog.timestamp < granica).delete()
        if deleted_count > 0:
            db.commit()
            print(f"Audit Cleanup: Obrisano {deleted_count} zapisa starijih od {days} dana.")
    except Exception as e:
        db.rollback()
        print(f"Greška pri čišćenju audit logova: {e}")