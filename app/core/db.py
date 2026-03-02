from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# MAJKA SVIH MODELA - Ovo je ono što ti nedostaje!
Base = declarative_base()

def get_db():
    """Ovisnost (dependency) koja osigurava zatvaranje sesije nakon svakog zahtjeva."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()