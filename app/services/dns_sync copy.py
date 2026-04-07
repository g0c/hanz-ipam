# v1.1.73
# DNS Sync Engine - Implementirana faza usklađivanja (brisanje nepostojećih DNS zapisa).

from sqlalchemy.orm import Session
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
    KOMENTAR: Sinkronizira DNS zone i uklanja zapise iz baze koji više ne postoje u DNS-u.
    """
    dns_zones = [zone.strip() for zone in settings.AD_DNS_ZONES.split(',')]
    
    total_added = 0
    total_updated = 0
    total_deleted = 0
    now = datetime.now()
    
    # KOMENTAR: Set u koji spremamo sve IP adrese pronađene u DNS-u tijekom skeniranja
    active_dns_ips = set()

    # --- 1. FAZA: AŽURIRANJE I DODAVANJE ---
    for zone in dns_zones:
        records = fetch_dns_records(zone)
        
        for rec in records:
            hostname = rec["hostname"].rstrip('.')
            ip_val = rec["ip"]

            # Filtriranje sistemskih i nepotrebnih zapisa
            if any(x in hostname.lower() for x in ["@", "*", "msdcs", "_udp", "_tcp"]):
                continue

            active_dns_ips.add(ip_val)

            device = db.query(Device).filter(Device.ip_addr == ip_val).first()
            detected_type = "Gateway" if ip_val.endswith(".1") else "Server"

            if device:
                # Ažuriranje postojećeg uređaja
                device.last_seen = now
                device.updated_by = "DNS_SYNC"
                
                if ip_val.endswith(".1") and device.device_type != "Gateway":
                    device.device_type = "Gateway"

                if not device.hostname or "unknown" in device.hostname.lower():
                    device.hostname = hostname
                total_updated += 1
            else:
                # Kreiranje novog uređaja
                new_device = Device(
                    ip_addr=ip_val,
                    hostname=hostname,
                    status=DeviceStatus.active,
                    environment="PROD",
                    device_type=detected_type,
                    last_seen=now,
                    created_by="DNS_SYNC",
                    updated_by="DNS_SYNC"
                )
                db.add(new_device)
                total_added += 1
    
    # Flush da osiguramo da su novi uređaji u sesiji prije čišćenja
    db.flush()

    # --- 2. FAZA: ČIŠĆENJE (RECONCILIATION) ---
    # KOMENTAR: Tražimo uređaje koje je kreirao DNS_SYNC, a kojih NEMA u aktivnom DNS-u
    stale_devices = db.query(Device).filter(
        Device.created_by == "DNS_SYNC",
        ~Device.ip_addr.in_(list(active_dns_ips))
    ).all()

    for stale_dev in stale_devices:
        # KOMENTAR: Bilježimo brisanje u Audit Log prije samog uklanjanja
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