import os
import asyncio
import logging # figure this out too
import traceback

# see if i can clean this up
from fastapi import FastAPI, HTTPException
#from pydantic import BaseModel
#import redis
#from rq import Queue
import asyncpg
from dotenv import load_dotenv

from schemas.db_model import DatabasePayload, ResponseModel, successful_response
from redis_config import task_queue
from app.workers import save_to_db

load_dotenv()
DATABASE_PASS = os.getenv('DATABASE_PASS')

app = FastAPI()

@app.post("/readings/fast")
async def post_reading(reading: DatabasePayload) -> ResponseModel: # verify if this should even be async
    """
    Push client request to Redis worker queue, return success
    """
    task_queue.enqueue(save_to_db, reading)
    return successful_response

@app.post("/readings/slow")
async def post_reading_slow(reading: DatabasePayload) -> ResponseModel:
    """
    Push client request directly to PostgreSQL, return success
    """    
    try: # attempt to make a connection to database
        conn = await asyncpg.connect(user='postgres', password=DATABASE_PASS, 
                                database='iot-firehose', host='127.0.0.1', port=5432)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail='Could not connect to database'
        )

    try:
        await conn.execute('''
            INSERT INTO readings (id, reading)
            VALUES ($1, $2)
        ''', [reading.id, reading.reading])
        await conn.commit()
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=400, # 400 bad request
            detail='Item already exists'
        )
    except Exception as e: # read more into postgres error codes
        print(f'Error occurred: {e}')
        logging.error(traceback.format_exc())
        raise
    finally:
        conn.close()

    return successful_response