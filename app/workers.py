# to do: create loop to pull from redis and push to postgres
import asyncio

import asyncpg

from redis_config import redis_client

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