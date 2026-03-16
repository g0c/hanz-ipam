# v1.1.72
# Dodana logika za prepoznavanje Gateway uređaja (.1) i optimiziran poziv mapiranja.

from sqlalchemy.orm import Session
from datetime import datetime
from app.core.config import settings
from app.core.models import Device, DeviceStatus, Subnet
from app.services.dns_service import fetch_dns_records
import ipaddress

# KOMENTAR: Funkcija koja povezuje uređaje bez podmreže s postojećim CIDR-ovima u bazi
def map_devices_to_subnets(db: Session):
    """
    Prolazi kroz sve uređaje koji nemaju subnet_id i provjerava pripadaju li nekoj podmreži.
    """
    subnets = db.query(Subnet).all()
    # Tražimo samo uređaje koji su 'siročad' (nemaju subnet_id)
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

# KOMENTAR: Glavna funkcija za sinkronizaciju DNS zapisa u bazu
def run_dns_sync(db: Session):
    dns_zones = [zone.strip() for zone in settings.AD_DNS_ZONES.split(',')]
    
    total_added = 0
    total_updated = 0
    now = datetime.now()
    
    # KOMENTAR: Pratimo IP adrese koje smo već obradili u ovoj sesiji kako bismo izbjegli duplikate
    processed_ips = set()

    for zone in dns_zones:
        records = fetch_dns_records(zone)
        
        for rec in records:
            hostname = rec["hostname"].rstrip('.')
            ip_val = rec["ip"]

            # Filtriranje sistemskih zapisa
            if any(x in hostname.lower() for x in ["@", "*", "msdcs", "_udp", "_tcp"]):
                continue

            if ip_val in processed_ips:
                continue

            device = db.query(Device).filter(Device.ip_addr == ip_val).first()

            # KOMENTAR: Logika za određivanje tipa uređaja (Gateway za .1, inače Server)
            detected_type = "Gateway" if ip_val.endswith(".1") else "Server"

            if device:
                # Ažuriranje postojećeg uređaja
                device.last_seen = now
                device.updated_by = "DNS_SYNC"
                
                # Ako je detektiran kao gateway, ažuriraj tip ako već nije postavljen
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
                    updated_by="DNS_SYNC",
                    created_at=now
                )
                db.add(new_device)
                db.flush() 
                total_added += 1
            
            processed_ips.add(ip_val)

    # KOMENTAR: Commitamo sve promjene nakon što prođemo sve zone
    db.commit()

    # KOMENTAR: Mapiranje na podmreže se radi JEDNOM nakon što su svi uređaji u bazi/flushani
    mapped = map_devices_to_subnets(db)
    print(f"Sync završen. Dodano: {total_added}, Ažurirano: {total_updated}, Mapirano: {mapped}")

    return total_added + total_updated