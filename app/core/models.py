# v1.0.5
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, BigInteger, Text
from datetime import datetime
import enum

# Osnovna klasa za sve SQLAlchemy modele
Base = declarative_base()

# Statusi uređaja usklađeni s MySQL ENUM tipom
class DeviceStatus(enum.Enum):
    active = "active"
    reserved = "reserved"
    offline = "offline"
    unknown = "unknown"

# Model korisnika sustava
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(255), unique=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(128))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

# Model mrežnog segmenta (Subnet) - DODANI STUPCI name I vlan_id
class Subnet(Base):
    __tablename__ = "subnets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cidr = Column(String(32), nullable=False)
    name = Column(String(128), nullable=True)     # Naziv mreže (npr. Produkcija)
    vlan_id = Column(Integer, nullable=True)     # VLAN ID (npr. 100)
    description = Column(String(255), nullable=True)
    
    devices = relationship("Device", back_populates="subnet")

# Glavni model mrežnog uređaja
class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hostname = Column(String(255), nullable=True)
    ip_addr = Column(String(45), unique=True, nullable=False)
    mac = Column(String(32), nullable=True)
    vendor = Column(String(128), nullable=True)
    status = Column(Enum(DeviceStatus), default=DeviceStatus.unknown)
    
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=True)
    
    subnet_id = Column(Integer, ForeignKey("subnets.id", ondelete="SET NULL"), nullable=True)
    subnet = relationship("Subnet", back_populates="devices")

    environment = Column(String(50), nullable=True) # PROD, TEST, DEV
    device_type = Column(String(50), nullable=True) # Server, VM, Network...
    created_by = Column(String(64), nullable=True)
    updated_by = Column(String(64), nullable=True)

# Model korisničke sesije
class Session(Base):
    __tablename__ = "sessions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="sessions")