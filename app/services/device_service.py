# v1.0.3
from sqlalchemy.orm import Session
from app.core.models import Device, DeviceStatus
import ipaddress
from datetime import datetime
import subprocess
import platform

# Dohvaća sve uređaje iz baze
def get_all_devices(db: Session):
    return db.query(Device).all()

# Dohvaća jedan uređaj prema ID-u
def get_device(db: Session, device_id: int):
    return db.query(Device).filter(Device.id == device_id).first()

# Kreiranje novog uređaja s auditom i poveznicom na subnet
def create_device(db: Session, hostname: str, ip_addr: str, status: str, 
                  device_type: str = None, environment: str = None,
                  mac: str = None, location: str = None, description: str = None, 
                  created_by: str = None, subnet_id: int = None):
    # Validacija IP adrese prije spremanja
    try:
        ipaddress.ip_address(ip_addr)
    except ValueError:
        raise ValueError("Neispravan format IP adrese.")

    db_device = Device(
        hostname=hostname,
        ip_addr=ip_addr,
        status=DeviceStatus(status),
        device_type=device_type,
        environment=environment,
        mac=mac,
        location=location,
        description=description,
        created_by=created_by,
        subnet_id=subnet_id, # Ispravljeno: subnet_id je sada parametar
        created_at=datetime.utcnow()
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

# Ažuriranje uređaja s praćenjem tko je zadnji mijenjao podatke
def update_device(db: Session, device_id: int, hostname: str, ip_addr: str, status: str,
                  device_type: str = None, environment: str = None,
                  mac: str = None, location: str = None, description: str = None,
                  updated_by: str = None, subnet_id: int = None):
    db_device = get_device(db, device_id)
    if db_device:
        # Validacija IP adrese
        ipaddress.ip_address(ip_addr)
        
        db_device.hostname = hostname
        db_device.ip_addr = ip_addr
        db_device.status = DeviceStatus(status)
        db_device.device_type = device_type
        db_device.environment = environment
        db_device.mac = mac
        db_device.location = location
        db_device.description = description
        db_device.updated_by = updated_by
        db_device.subnet_id = subnet_id # Omogućuje premještanje uređaja u drugi subnet
        
        db.commit()
        db.refresh(db_device)
    return db_device

# Trajno brisanje uređaja iz baze
def delete_device(db: Session, device_id: int):
    db_device = get_device(db, device_id)
    if db_device:
        db.delete(db_device)
        db.commit()
        return True
    return False

# Izvršava ICMP ping i ažurira status i vrijeme zadnjeg odziva (Last Seen)
def ping_device(db: Session, device_id: int):
    device = get_device(db, device_id)
    if not device:
        return None

    # Određivanje ping parametara ovisno o operacijskom sustavu servera
    # -n 1 za Windows, -c 1 za Linux/Unix
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    # -W 2 postavlja timeout na 2 sekunde
    command = ['ping', param, '1', '-W', '2', device.ip_addr]

    # Pokretanje sistemske naredbe
    res = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Ako je returncode 0, ping je prošao (uređaj je online)
    if res.returncode == 0:
        device.status = DeviceStatus.active
        device.last_seen = datetime.utcnow()
        success = True
    else:
        device.status = DeviceStatus.offline
        success = False

    db.commit()
    db.refresh(device)
    
    # Vraćamo podatke koje JavaScript u tablici uređaja očekuje za ažuriranje UI-a
    return {
        "success": success,
        "status": device.status.value,
        "last_seen": device.last_seen.strftime("%Y-%m-%d %H:%M:%S") if device.last_seen else "Nikada"
    }