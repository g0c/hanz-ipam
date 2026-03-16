# v1.1.1
# Kompletni modeli usklađeni s MySQL bazom i sustavom ovisnosti.

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.db import Base

class DeviceStatus(enum.Enum):
    active = "active"
    reserved = "reserved"
    offline = "offline"
    unknown = "unknown"

class User(Base):
    """Model korisnika usklađen s DESCRIBE users ispisom."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    full_name = Column(String(128), nullable=True)
    
    # OVO JE NEDOSTAJALO:
    is_active = Column(Boolean, default=True) 
    
    role = Column(String(20), default="user")
    mfa_secret = Column(String(64), nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

class Subnet(Base):
    __tablename__ = "subnets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    cidr = Column(String(45), unique=True, nullable=False)
    vlan_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    devices = relationship("Device", back_populates="subnet")

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(100), nullable=False)
    ip_addr = Column(String(45), unique=True, index=True, nullable=False)
    mac = Column(String(17), nullable=True)
    vendor = Column(String(100), nullable=True)
    status = Column(Enum(DeviceStatus), default=DeviceStatus.unknown)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, nullable=True)
    subnet_id = Column(Integer, ForeignKey("subnets.id"), nullable=True)
    environment = Column(String(20), default="PROD")
    device_type = Column(String(50), default="Server")
    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    subnet = relationship("Subnet", back_populates="devices")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    username = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)
    target_type = Column(String(20), nullable=False)
    target_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    source_ip = Column(String(45), nullable=True)