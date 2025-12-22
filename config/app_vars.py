import os
from dotenv import load_dotenv

# ---------- Enter/set configs in environment or locally ----------
load_dotenv()
# Database settings:
USER = 'postgres'
DATABASE = 'iot-firehose'
HOST = '127.0.0.1'
PORT = 5432
DATABASE_PASS = os.getenv('DATABASE_PASS') # Password to PostgreSQL database
MIN_SIZE: int = 10 # Minimum number of connections asyncpg connection pool is initialized with
MAX_SIZE: int = 10 # Maximum number of connections in asyncpg connection pool
CLEAR_DB: bool = bool(os.getenv('CLEAR_DB', False)) # Automatically clear the database on startup

# Logging settings:
VERBOSE: bool = bool(os.getenv('VERBOSE', False)) # Enable debug messages for tracking event loop
CLEAR_LOG: bool = bool(os.getenv('CLEAR_LOG', False)) # Automatically clear the debug.log on startup
# -----------------------------------------------------------------