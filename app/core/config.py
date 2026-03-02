# v1.0.4
# Konfiguracija aplikacije - IPAM projekt.

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Naziv aplikacije
    APP_NAME: str = "IPAM"
    
    # Tajni ključ za JWT - koristimo IPAM_ prefiks
    SECRET_KEY: str = os.getenv("IPAM_SECRET_KEY", "super-tajni-kljuc-promijeni-me")
    
    # Algoritam za enkripciju
    JWT_ALGO: str = "HS256"
    
    # Trajanje tokena (7 dana = 10080 minuta)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("IPAM_TOKEN_EXPIRE", "10080"))
    
    # URL baze podataka
    DATABASE_URL: str = os.getenv("IPAM_DATABASE_URL", "mysql+mysqlconnector://ipam:password@localhost/ipam")
    
    # OpenAI API ključ (uvijek bez prefiksa prema tvojem pravilu)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

settings = Settings()