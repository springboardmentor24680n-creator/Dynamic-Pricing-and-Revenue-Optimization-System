"""
PricePilot AI - Configuration Settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    APP_NAME: str = "PricePilot AI - Dynamic Pricing & Revenue Intelligence System"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/dynamic_pricing"
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "pricepilot_ai"
    
    # Security
    SECRET_KEY: str = "pricepilot-ai-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    
    # Data
    DATA_DIR: str = "data_uploaded"
    
    # Trained model artifacts (joblib files) live here
    MODEL_DIR: str = "ml_models"
    
    # Auth
    RESET_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    
    # Email (SMTP) - used for approval/rejection notifications
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "PricePilot AI <noreply@pricepilot.ai>"
    SMTP_USE_TLS: bool = True
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
print("GOOGLE_CLIENT_ID =", settings.GOOGLE_CLIENT_ID)
print("ENV FILE LOADED")