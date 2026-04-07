# v1.1.77
# DNS Sync Engine - KONAČNO RJEŠENJE: Native MySQL "ON DUPLICATE KEY UPDATE"
# Zaobilazimo SQLAlchemy Session cache kako bi MySQL baza sama riješila upsert bez grešaka.

from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert  # KOMENTAR: Uvozimo MySQL specifičnu naredbu
from datetime import datetime
import ipaddress

from app.core.config import settings
from app.core.models import Device, DeviceStatus, Subnet
from app.services.dns_service import fetch_dns_records
from app.services import audit_service

def map_devices_to_subnets(db: Session):
    """
    KOMENTAR: Povezuje uređaje bez podmreže s postojećim CIDR-ovima u bazi.
    """
    subnets = db.query(Subnet).all()
    orphans = db.query(Device).filter(Device.subnet_id == None).all()
    
    mapped_count = 0
    for device in orphans:
        try:
            d_ip = ipaddress.ip_address(device.ip_addr)
            for sn in subnets:
                net = ipaddress.ip_network(sn.cidr)
                if d_ip in net:
                    device.subnet_id = sn.id
                    mapped_count += 1
                    break
        except ValueError:
            continue
            
    db.commit()
    return mapped_count

def run_dns_sync(db: Session):
    """
    KOMENTAR: Sinkronizira DNS koristeći izvorni MySQL Upsert.
    """
    dns_zones = [zone.strip() for zone in settings.AD_DNS_ZONES.split(',')]
    
    total_added = 0
    total_updated = 0
    total_deleted = 0
    now = datetime.now()
    
    active_dns_ips = set()

    # --- 1. FAZA: AŽURIRANJE I DODAVANJE (MySQL Native Upsert) ---
    for zone in dns_zones:
        records = fetch_dns_records(zone)
        
        for rec in records:
            hostname = str(rec["hostname"]).strip().rstrip('.')
            raw_ip = str(rec["ip"]).strip()

            try:
                ip_obj = ipaddress.ip_address(raw_ip)
                ip_val = str(ip_obj)
            except ValueError:
                continue

            if any(x in hostname.lower() for x in ["@", "*", "msdcs", "_udp", "_tcp"]):
                continue

            # I dalje filtriramo duplikate iz samog DNS-a unutar istog skeniranja
            if ip_val in active_dns_ips:
                continue

            active_dns_ips.add(ip_val)
            detected_type = "Gateway" if ip_val.endswith(".1") else "Server"

            # KOMENTAR: Konstruiramo MySQL specifičnu INSERT naredbu
            stmt = insert(Device).values(
                ip_addr=ip_val,
                hostname=hostname,
                status=DeviceStatus.active,
                environment="PROD",
                device_type=detected_type,
                last_seen=now,
                created_by="DNS_SYNC",
                updated_by="DNS_SYNC"
            )

            # KOMENTAR: Definiramo što se događa ako MySQL detektira Duplicate Entry grešku
            update_dict = {
                "hostname": stmt.inserted.hostname,
                "last_seen": stmt.inserted.last_seen,
                "updated_by": "DNS_SYNC"
            }
            
            if ip_val.endswith(".1"):
                update_dict["device_type"] = "Gateway"

            on_duplicate_stmt = stmt.on_duplicate_key_update(**update_dict)

            # KOMENTAR: Izvršavamo izravno u bazi, zaobilazeći Pythonov ORM session cache!
            result = db.execute(on_duplicate_stmt)
            
            # U MySQL-u: rowcount 1 znači Insert, rowcount 2 znači Update
            if result.rowcount == 1:
                total_added += 1
            else:
                total_updated += 1
    
    # Ovdje radimo commit svih izvršenih naredbi prije čišćenja
    db.commit()

    # --- 2. FAZA: ČIŠĆENJE (RECONCILIATION) ---
    # KOMENTAR: Sigurnosna provjera - brišemo samo ako smo uspjeli pročitati barem nešto iz DNS-a
    if active_dns_ips:  
        stale_devices = db.query(Device).filter(
            Device.created_by == "DNS_SYNC",
            ~Device.ip_addr.in_(list(active_dns_ips))
        ).all()

        for stale_dev in stale_devices:
            audit_service.log_event(
                db,
                username="DNS_SYNC",
                action="DELETE",
                target_type="DEVICE",
                target_id=stale_dev.id,
                details=f"Uređaj {stale_dev.hostname} ({stale_dev.ip_addr}) automatski uklonjen - ne postoji u DNS-u.",
                source_ip="127.0.0.1"
            )
            db.delete(stale_dev)
            total_deleted += 1

        db.commit()

    # --- 3. FAZA: MAPIRANJE ---
    mapped = map_devices_to_subnets(db)
    
    print(f"Sync završen. Dodano: {total_added}, Ažurirano: {total_updated}, Obrisano: {total_deleted}, Mapirano: {mapped}")

    return {
        "added": total_added, 
        "updated": total_updated, 
        "deleted": total_deleted, 
        "mapped": mapped
    }