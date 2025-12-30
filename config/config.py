from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
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
    
    # Redis settings:
    STREAM_NAME: str = 'db_buffer'
    CONSUMER_GROUP: str = 'workers'
    CONSUMER_NAME: str = 'worker1'
    CLEAR_STREAM: bool = False
    BUFFER: int = 100
    # -----------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = AppSettings() # type: ignore