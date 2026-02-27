from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.models import Device
from datetime import datetime
from app.services.validate import validate_ip

def get_all_devices(db: Session):
    return db.query(Device).order_by(Device.id).all()

def get_devices_page(db: Session, page: int = 1, per_page: int = 25):
    offset = (page - 1) * per_page
    devices = db.query(Device).order_by(Device.id).offset(offset).limit(per_page).all()

    next_page_exists = len(devices) == per_page

    return devices, next_page_exists

def get_device(db: Session, device_id: int):
    return db.query(Device).filter(Device.id == device_id).first()

def create_device(db: Session, hostname: str, ip_addr: str, status: str = "unknown"):
    hostname = hostname.strip()
    ip_addr = validate_ip(ip_addr)

    dev = Device(
        hostname=hostname,
        ip_addr=ip_addr,
        status=status,
        last_seen=None
    )
    db.add(dev)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise IntegrityError("duplicate", None, None)
    db.refresh(dev)
    return dev

def update_device(db: Session, device_id: int, hostname: str, ip_addr: str, status: str):
    dev = get_device(db, device_id)
    if not dev:
        return None

    hostname = hostname.strip()
    ip_addr = validate_ip(ip_addr)

    dev.hostname = hostname
    dev.ip_addr = ip_addr
    dev.status = status

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise IntegrityError("duplicate", None, None)

    return dev

def delete_device(db: Session, device_id: int):
    dev = get_device(db, device_id)
    if not dev:
        return False
    db.delete(dev)
    db.commit()
    return True
