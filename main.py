import os
import asyncio
import logging

from fastapi import FastAPI
import redis
import asyncpg
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

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

if __name__ == '__main__':
    asyncio.run(run())