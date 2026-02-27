# v1.0.1
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, BigInteger
from datetime import datetime
import enum

Base = declarative_base()

# Definicija statusa uređaja prema MySQL ENUM tipu
class DeviceStatus(enum.Enum):
    active = "active"
    reserved = "reserved"
    offline = "offline"
    unknown = "unknown"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(255), unique=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(128))
    is_active = Column(Boolean, default=True)
    mfa_secret = Column(String(64), nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Dvosmjerna relacija prema sesijama
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)

class Subnet(Base):
    __tablename__ = "subnets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cidr = Column(String(32), nullable=True)
    description = Column(String(255), nullable=True)

    # Relacija prema uređajima koji pripadaju ovom subnetu
    devices = relationship("Device", back_populates="subnet")

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hostname = Column(String(255), nullable=True)
    ip_addr = Column(String(45), unique=True, nullable=False)
    status = Column(Enum(DeviceStatus), default=DeviceStatus.unknown)
    mac = Column(String(32), nullable=True)
    vendor = Column(String(128), nullable=True)
    last_seen = Column(DateTime, nullable=True)
    
    # Strani ključ s postavljenim SET NULL ukoliko se subnet obriše
    subnet_id = Column(Integer, ForeignKey("subnets.id", ondelete="SET NULL"), nullable=True)

    # Povratna relacija prema Subnet klasi
    subnet = relationship("Subnet", back_populates="devices")

class Session(Base):
    __tablename__ = "sessions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(String(64), unique=True, nullable=False)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Povratna relacija prema korisniku
    user = relationship("User", back_populates="sessions")

class AuthLog(Base):
    __tablename__ = "auth_log"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=True)
    success = Column(Boolean, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)