# v1.0.0
# Audit Engine - Servis za trajno bilježenje aktivnosti u IPAM sustavu.

from sqlalchemy.orm import Session
from app.core.models import AuditLog

def log_event(db: Session, username: str, action: str, target_type: str, 
              target_id: int = None, details: str = None, source_ip: str = None):
    """
    Glavna funkcija za upisivanje događaja u revizijsku tablicu (Audit Log).
    
    Parametri:
    - db: Aktivna sesija baze podataka.
    - username: Tko je izvršio akciju (korisnik ili sustav).
    - action: Tip akcije (CREATE, UPDATE, DELETE, DISCOVERY, STATUS_CHANGE).
    - target_type: Na što se akcija odnosi (DEVICE, SUBNET).
    - target_id: Jedinstveni ID objekta nad kojim je izvršena akcija.
    - details: Tekstualni opis promjene.
    - source_ip: IP adresa s koje je došao zahtjev (ako postoji).
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
        # Ne radimo refresh ovdje jer nam objekt najčešće ne treba odmah natrag
    except Exception as e:
        # U slučaju greške kod logiranja, radimo rollback da ne blokiramo sesiju
        db.rollback()
        print(f"Kritična greška u Audit servisu: {e}")