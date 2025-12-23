import os

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()
class Settings(BaseSettings):
    # ---------- Enter/set configs in environment or locally ----------
    # Database settings:
    USER: str = 'postgres'
    DATABASE: str
    DATABASE_PASS: str
    HOST: str = '127.0.0.1'
    PORT: int = 5432
    MIN_SIZE: int = 10 # Minimum number of connections asyncpg connection pool is initialized with
    MAX_SIZE: int = 10 # Maximum number of connections asyncpg connection pool is initialized with
    CLEAR_DB: bool = False # Automatically clear the database on startup

    # Logging settings:
    VERBOSE: bool = False # Enable debug messages for tracking event loop
    CLEAR_LOG: bool = True # Automatically clear the debug.log on startup

    # -----------------------------------------------------------------
    parent_dir = Path(__file__).resolve().parent.parent.parent
    env_path = parent_dir / ".env"
    model_config = SettingsConfigDict(env_file=env_path)

settings = Settings() # type: ignore