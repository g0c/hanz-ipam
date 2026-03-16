# v1.1.52
# Konfiguracija aplikacije - centralizirane postavke za IPAM i AD.

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Učitavanje .env datoteke
load_dotenv()

class Settings(BaseSettings):
    # Naziv aplikacije
    APP_NAME: str = "IPAM"
    
    # Tajni ključ za JWT (ostavljamo bez prefiksa radi jednostavnosti ili po želji)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-tajni-kljuc-promijeni-me")
    
    # Algoritam za enkripciju
    JWT_ALGO: str = "HS256"
    ALGORITHM: str = "HS256" # Dodano radi kompatibilnosti s main.py
    
    # Trajanje tokena (7 dana = 10080 minuta)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("TOKEN_EXPIRE", "10080"))
    
    # URL baze podataka
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+mysqlconnector://ipam:password@localhost/ipam")
    
    # OpenAI API ključ (uvijek bez prefiksa prema pravilu)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Active Directory (AD) postavke - bez posebnog prefiksa
    AD_SERVER: str = os.getenv("AD_SERVER")
    AD_DOMAIN: str = os.getenv("AD_DOMAIN")
    AD_BASE_DN: str = os.getenv("AD_BASE_DN")
    AD_BIND_USER: str = os.getenv("AD_BIND_USER")
    AD_BIND_PASS: str = os.getenv("AD_BIND_PASS")
    AD_DNS_ZONES: str = os.getenv("AD_DNS_ZONES", "")

    class Config:
        case_sensitive = True

settings = Settings()