# v1.0.1
from sqlalchemy.orm import Session
from app.core.models import Device, DeviceStatus
import ipaddress

# Dohvaća sve uređaje iz baze za prikaz u tablici
def get_all_devices(db: Session):
    return db.query(Device).all()

# Dohvaća jedan uređaj prema njegovom ID-u
def get_device(db: Session, device_id: int):
    return db.query(Device).filter(Device.id == device_id).first()

# Kreira novi uređaj u bazi podataka sa svim metapodacima
def create_device(db: Session, hostname: str, ip_addr: str, status: str, 
                  mac: str = None, location: str = None, description: str = None):
    # Validacija IP adrese prije unosa
    try:
        ipaddress.ip_address(ip_addr)
    except ValueError:
        raise ValueError("Neispravan format IP adrese.")

    db_device = Device(
        hostname=hostname,
        ip_addr=ip_addr,
        status=DeviceStatus(status),
        mac=mac,
        location=location,
        description=description
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

# Ažurira postojeći uređaj u bazi
def update_device(db: Session, device_id: int, hostname: str, ip_addr: str, status: str,
                  mac: str = None, location: str = None, description: str = None):
    db_device = get_device(db, device_id)
    if db_device:
        db_device.hostname = hostname
        db_device.ip_addr = ip_addr
        db_device.status = DeviceStatus(status)
        db_device.mac = mac
        db_device.location = location
        db_device.description = description
        db.commit()
        db.refresh(db_device)
    return db_device

# Briše uređaj iz baze podataka
def delete_device(db: Session, device_id: int):
    db_device = get_device(db, device_id)
    if db_device:
        db.delete(db_device)
        db.commit()
        return True
    return False