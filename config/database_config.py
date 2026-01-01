import asyncpg
from asyncpg import Pool
from psycopg2.pool import ThreadedConnectionPool

async def create_async_db_pool(
        USER: str, 
        DATABASE: str,
        HOST: str,
        PORT: int,
        DATABASE_PASS: str, 
        MIN_SIZE: int = 10, 
        MAX_SIZE: int = 10) -> Pool:
    return await asyncpg.create_pool(
        user=USER, 
        password=DATABASE_PASS, 
        database=DATABASE, 
        host=HOST, 
        port=PORT,
        min_size=MIN_SIZE,
        max_size=MAX_SIZE
    )

async def clear_db(DATABASE_PASS: str, CLEAR_DB: bool = False) -> None:
    if CLEAR_DB:
        conn = await asyncpg.connect(user='postgres', password=DATABASE_PASS, 
                                database='iot-firehose', host='127.0.0.1', port=5432)
        async with conn.transaction():
            await conn.execute('''
                    TRUNCATE TABLE readings
                ''') # clears the readings database