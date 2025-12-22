import asyncio

import asyncpg

from config.redis_config import task_queue
from schemas.db_model import DatabasePayload

async def save_to_db(reading: DatabasePayload):
    """
    Read from Redis queue and push to Postgres database
    """
    pass

"""
# just testing for now
async def run():
    conn = await asyncpg.connect(user='postgres', password=os.getenv('DATABASE_PASS'), database='iot-firehose', host='127.0.0.1', port=5432)

    await conn.execute('TRUNCATE TABLE readings')

    await conn.execute('''
INSERT INTO readings (id, reading) VALUES
                       (1, 67),
                       (2, 88);
''')
    
    row = await conn.fetch('SELECT * FROM readings;')
    for r in row:
        print(r)

    await conn.close()
"""