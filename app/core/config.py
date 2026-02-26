import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "IPAM"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")
    JWT_ALGO: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+mysqlconnector://ipam:password@localhost/ipam")

settings = Settings()