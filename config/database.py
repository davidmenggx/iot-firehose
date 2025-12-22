import os

import asyncpg
from dotenv import load_dotenv

async def create_db_pool(DATABASE_PASS: str, MIN_SIZE: int = 10, MAX_SIZE: int = 10):
    return await asyncpg.create_pool(
        user='postgres', 
        password=DATABASE_PASS, 
        database='iot-firehose', 
        host='127.0.0.1', 
        port=5432,
        min_size=MIN_SIZE,
        max_size=MAX_SIZE
    )