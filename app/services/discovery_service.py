# v1.0.3
# Discovery Engine - Potpuna verzija s ping_ip funkcijom i ispravljenim audit logiranjem.

import subprocess
import platform
import ipaddress
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from sqlalchemy.orm import Session

# Uvoz modela i servisa
from app.core.models import Device, Subnet, DeviceStatus
from app.services import audit_service

def ping_ip(ip: str):
    """
    Izvršava jedan ICMP ping prema zadanoj adresi.
    Prilagođeno za Linux (-c) i Windows (-n) sustave.
    """
    # Određivanje parametra ovisno o operacijskom sustavu servera
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
    timeout_val = '1000' if platform.system().lower() == 'windows' else '1'
    
    command = ['ping', param, '1', timeout_param, timeout_val, ip]
    
    try:
        result = subprocess.run(
            command, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            timeout=2 
        )
        return result.returncode == 0
    except Exception:
        return False

def scan_single_ip(db: Session, ip_str: str, subnet_id: int):
    """
    Skenira pojedinačnu IP adresu, uspoređuje s bazom i bilježi promjene uz ispravan source_ip.
    """
    is_online = ping_ip(ip_str)
    device = db.query(Device).filter(Device.ip_addr == ip_str).first()
    
    # KOMENTAR: Za Discovery Engine koristimo lokalnu adresu kao izvor akcije
    discovery_ip = "127.0.0.1"

    if is_online:
        if device:
            old_status = device.status.value
            device.status = DeviceStatus.active
            device.last_seen = datetime.now()
            
            if old_status != 'active':
                audit_service.log_event(
                    db, 
                    username="Discovery Engine", 
                    action="STATUS_CHANGE", 
                    target_type="DEVICE", 
                    target_id=device.id, 
                    details=f"Uređaj {ip_str} ponovno online.",
                    source_ip=discovery_ip
                )
            
            if not device.subnet_id:
                device.subnet_id = subnet_id
        else:
            new_dev = Device(
                hostname=f"Unknown-{ip_str.split('.')[-1]}",
                ip_addr=ip_str,
                status=DeviceStatus.active,
                last_seen=datetime.now(),
                subnet_id=subnet_id,
                description="Automatski otkriven putem mrežnog skeniranja.",
                device_type="Other",
                environment="DEV",
                created_by="Discovery Engine"
            )
            db.add(new_dev)
            db.flush() 
            
            audit_service.log_event(
                db, 
                username="Discovery Engine", 
                action="DISCOVERY", 
                target_type="DEVICE", 
                target_id=new_dev.id, 
                details=f"Pronađen novi host na mreži: {ip_str}",
                source_ip=discovery_ip
            )
    else:
        if device and device.status == DeviceStatus.active:
            device.status = DeviceStatus.offline
            audit_service.log_event(
                db, 
                username="Discovery Engine", 
                action="STATUS_CHANGE", 
                target_type="DEVICE", 
                target_id=device.id, 
                details=f"Uređaj {ip_str} više ne odgovara (Offline).",
                source_ip=discovery_ip
            )
            
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Greška pri spremanju discovery rezultata za {ip_str}: {e}")

def run_subnet_scan(db: Session, subnet_id: int):
    """
    Glavna funkcija koja pokreće paralelno skeniranje cijele podmreže.
    """
    subnet = db.query(Subnet).filter(Subnet.id == subnet_id).first()
    if not subnet:
        print(f"Subnet {subnet_id} nije pronađen.")
        return False
    
    try:
        network = ipaddress.ip_network(subnet.cidr)
        hosts = [str(ip) for ip in network.hosts()]
        
        print(f"[*] Pokrećem skeniranje subneta: {subnet.cidr} ({len(hosts)} adresa)...")
        
        with ThreadPoolExecutor(max_workers=30) as executor:
            for ip in hosts:
                executor.submit(scan_single_ip, db, ip, subnet_id)
        
        print(f"[+] Skeniranje subneta {subnet.cidr} završeno.")
        return True
        
    except Exception as e:
        print(f"Kritična greška u Discovery Engine-u za subnet {subnet_id}: {e}")
        return False