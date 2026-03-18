# v1.2.0
# Discovery Engine TURBO - Asinkrona verzija s asyncio semaforima.
# Omogućuje ekstremno brzo skeniranje podmreža uz minimalno opterećenje resursa.

import asyncio
import platform
import ipaddress
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.models import Device, Subnet, DeviceStatus
from app.services import audit_service

async def async_ping(ip: str, semaphore: asyncio.Semaphore):
    """Izvršava jedan asinkroni ICMP ping."""
    async with semaphore:
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
        timeout_val = '1000' if platform.system().lower() == 'windows' else '1'

        proc = await asyncio.create_subprocess_exec(
            'ping', param, '1', timeout_param, timeout_val, ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        return ip, proc.returncode == 0

def process_scan_result(db: Session, ip_str: str, is_online: bool, subnet_id: int):
    """Obrađuje rezultat skeniranja i zapisuje promjene u bazu (sinkrono)."""
    device = db.query(Device).filter(Device.ip_addr == ip_str).first()
    discovery_ip = "127.0.0.1"

    if is_online:
        if device:
            old_status = device.status.value if hasattr(device.status, 'value') else str(device.status)
            device.status = DeviceStatus.active
            device.last_seen = datetime.now()
            
            if old_status != 'active':
                audit_service.log_event(
                    db, username="Discovery Turbo", action="STATUS_CHANGE",
                    target_type="DEVICE", target_id=device.id,
                    details=f"Uređaj {ip_str} ponovno online.",
                    source_ip=discovery_ip
                )
        else:
            # Automatsko otkrivanje novog uređaja
            new_dev = Device(
                hostname=f"Unknown-{ip_str.split('.')[-1]}",
                ip_addr=ip_str,
                status=DeviceStatus.active,
                last_seen=datetime.now(),
                subnet_id=subnet_id,
                description="Otkriven asinkronim skeniranjem.",
                device_type="Other",
                environment="DEV",
                created_by="Discovery Turbo"
            )
            db.add(new_dev)
            db.flush()
            audit_service.log_event(
                db, username="Discovery Turbo", action="DISCOVERY",
                target_type="DEVICE", target_id=new_dev.id,
                details=f"Novi host pronađen: {ip_str}",
                source_ip=discovery_ip
            )
    else:
        # Ako je bio aktivan, a sad je offline
        if device and (device.status == DeviceStatus.active or device.status == 'active'):
            device.status = DeviceStatus.offline
            audit_service.log_event(
                db, username="Discovery Turbo", action="STATUS_CHANGE",
                target_type="DEVICE", target_id=device.id,
                details=f"Uređaj {ip_str} prestao odgovarati.",
                source_ip=discovery_ip
            )

async def run_subnet_scan(db: Session, subnet_id: int):
    """Pokreće asinkrono skeniranje i sinkronu obradu rezultata."""
    subnet = db.query(Subnet).filter(Subnet.id == subnet_id).first()
    if not subnet: return False

    try:
        network = ipaddress.ip_network(subnet.cidr)
        hosts = [str(ip) for ip in network.hosts()]
        
        # Ograničavamo na 50 konkurentnih procesa da ne zagušimo mrežni stack
        semaphore = asyncio.Semaphore(50)
        tasks = [async_ping(ip, semaphore) for ip in hosts]
        
        print(f"[*] TURBO SCAN START: {subnet.cidr}...")
        results = await asyncio.gather(*tasks)
        
        # Obrada rezultata u bazi
        for ip, is_online in results:
            process_scan_result(db, ip, is_online, subnet_id)
        
        db.commit()
        print(f"[+] TURBO SCAN DONE: {subnet.cidr}")
        return True
    except Exception as e:
        db.rollback()
        print(f"Kritična greška u Discovery Turbo: {e}")
        return False