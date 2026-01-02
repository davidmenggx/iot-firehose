import asyncpg
from asyncpg import Pool

async def create_async_db_pool(
        USER: str, 
        DATABASE: str,
        HOST: str,
        PORT: int,
        DATABASE_PASS: str, 
        MIN_SIZE: int = 10, 
        MAX_SIZE: int = 10) -> Pool:
    """Creates an asnycpg connection pool using settings from config"""
    return await asyncpg.create_pool(
        user=USER, 
        password=DATABASE_PASS, 
        database=DATABASE, 
        host=HOST, 
        port=PORT,
        min_size=MIN_SIZE,
        max_size=MAX_SIZE
    )

async def clear_db(DATABASE_PASS: str, CLEAR_DB: bool = False, CLEAR_DB2: bool = False) -> None:
    """
    Clears the readings and readings2 databases based on settings from config
    For testing, set to True to avoid duplicate primary key errors in readings
    """
    if CLEAR_DB:
        conn = await asyncpg.connect(user='postgres', password=DATABASE_PASS, 
                                database='iot-firehose', host='127.0.0.1', port=5432)
        async with conn.transaction():
            await conn.execute('''
                    TRUNCATE TABLE readings
                ''') # clears the readings database
    if CLEAR_DB2:
        conn = await asyncpg.connect(user='postgres', password=DATABASE_PASS, 
                                database='iot-firehose', host='127.0.0.1', port=5432)
        async with conn.transaction():
            await conn.execute('''
                    TRUNCATE TABLE readings2 RESTART IDENTITY
                ''') # clears the readings2 database and restarts the id column at 1