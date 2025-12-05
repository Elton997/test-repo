# app/core/config.py
import os
from pathlib import Path
from typing import Dict, Literal, Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


# Project root: dcim_backend_fastapi/
BASE_DIR = Path(__file__).resolve().parent.parent.parent


_loaded_env_file: Optional[str] = None
_env_load_warning: Optional[str] = None


def load_environment() -> None:
    """
    Load environment variables from an .env file based on APP_ENV.

    APP_ENV=dev  -> .env.dev
    APP_ENV=uat  -> .env.uat  (optional if you create it)
    APP_ENV=prod -> .env.prod
    APP_ENV=test -> .env.test

    If file is missing, it just relies on system env vars.
    """
    app_env = os.getenv("APP_ENV", "dev").lower()

    global _loaded_env_file, _env_load_warning

    env_map = {
        "dev": ".env.dev",
        "uat": ".env.uat",
        "prod": ".env.prod",
        "test": ".env.test",
    }

    env_file_name = env_map.get(app_env, ".env.dev")
    env_path = BASE_DIR / env_file_name

    if env_path.exists():
        load_dotenv(env_path)
        _loaded_env_file = str(env_path)
        _env_load_warning = None
    else:
        _loaded_env_file = None
        _env_load_warning = f"Env file {env_path} not found. Using system environment variables only."


class Settings(BaseSettings):
    # Environment: dev, uat, or prod
    ENVIRONMENT: Literal["dev", "uat", "prod"] = "dev"

    # Logging configuration
    LOG_LEVEL: str = "DEBUG"  # Will be overridden based on ENVIRONMENT
    LOG_FORMAT: Literal["json", "text"] = "json"
    LOG_FILE: Optional[str] = None  # e.g. "logs/app.log"

    # JWT configuration for token decoding
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    # LDAP configuration
    LDAP_SERVER_URI: str = os.getenv("LDAP_SERVER_URI", "ldap://localhost:389")
    LDAP_BASE_DN: str = os.getenv("LDAP_BASE_DN", "dc=example,dc=com")
    LDAP_BIND_DN: str = os.getenv("LDAP_BIND_DN", "")
    LDAP_BIND_PASSWORD: str = os.getenv("LDAP_BIND_PASSWORD", "")

    # SMTP / email configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    SMTP_TIMEOUT: int = int(os.getenv("SMTP_TIMEOUT", "30"))

    # Token expiration settings (in seconds)
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600 # 1 hour
    REFRESH_TOKEN_EXPIRE_SECONDS: int = 86400  # 1 day

    # Listing cache configuration (can be overridden via env vars)
    LISTING_CACHE_TTL_SECONDS: int = int(os.getenv("LISTING_CACHE_TTL_SECONDS", "30"))
    LISTING_CACHE_MAX_ENTRIES: int = int(os.getenv("LISTING_CACHE_MAX_ENTRIES", "256"))

    # Summary cache configuration (0 disables caching)
    SUMMARY_CACHE_TTL_SECONDS: int = int(os.getenv("SUMMARY_CACHE_TTL_SECONDS", "30"))

    # Change-log helper cache (entity name -> id lookups)
    CHANGELOG_ENTITY_CACHE_TTL_SECONDS: int = int(
        os.getenv("CHANGELOG_ENTITY_CACHE_TTL_SECONDS", "60")
    )
    
    # Device image storage configuration
    # DEVICE_IMAGE_STORAGE_PATH: str = os.getenv("DEVICE_IMAGE_STORAGE_PATH", str(BASE_DIR / "device_images"))
    DEVICE_IMAGE_STORAGE_PATH: str = os.getenv("DEVICE_IMAGE_STORAGE_PATH", str(BASE_DIR / "app/device_images"))
    
    # CORS configuration
    # Comma-separated list of allowed origins, or "*" for all origins
    # Example: "http://localhost:4200,http://localhost:3000"
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    class Config:
        # We already loaded the correct .env in load_environment()
        # so here we don't force any specific env_file.
        env_file = None
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set log level based on environment
        if self.ENVIRONMENT == "prod":
            object.__setattr__(self, "LOG_LEVEL", "INFO")
        else:  # dev or uat
            object.__setattr__(self, "LOG_LEVEL", "DEBUG")


# Lazy settings instance - only created on first access
_settings = None


def get_settings() -> Settings:
    """Lazy settings loader - settings are only created on first access."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# For backwards compatibility, use a proxy class
class _SettingsProxy:
    """Proxy that lazily loads settings on first attribute access."""
    
    def __getattr__(self, name):
        return getattr(get_settings(), name)
    
    def __repr__(self):
        return repr(get_settings())


settings = _SettingsProxy()


def get_env_load_state() -> Dict[str, Optional[str]]:
    """
    Helper for logging modules to know which env file was loaded.
    Returns dict with 'env_file' and optional 'warning'.
    """
    return {
        "env_file": _loaded_env_file,
        "warning": _env_load_warning,
    }
