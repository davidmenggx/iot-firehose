import os
import asyncio
import logging # figure this out too
import traceback
from contextlib import asynccontextmanager

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Create a context pool for the pooling endpoints to use
    """
    app.state.pool = await asyncpg.create_pool(user='postgres', password=DATABASE_PASS, 
                                database='iot-firehose', host='127.0.0.1', port=5432)
    yield
    await app.state.pool.close()

app = FastAPI(lifespan=lifespan) # read up on what lifespan is

@app.post("/readings/fast")
async def post_reading(reading: DatabasePayload) -> ResponseModel:
    """
    Push client request to Redis worker queue, return success
    """
    task_queue.enqueue(save_to_db, reading)
    return successful_response

@app.post("/readings/slow/nonpooling")
async def post_reading_slow_nonpooling(reading: DatabasePayload) -> ResponseModel:
    """
    Push client request directly to PostgreSQL without connection pooling, return success
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
        async with conn.transaction(): # important: use context manager to automatically commit on cleanup
            await conn.execute('''
                INSERT INTO readings (id, reading, timestamp)
                VALUES ($1, $2, $3)
            ''', reading.id, reading.reading, reading.timestamp) # pass in the positional args for the sql query as separate args, not a list
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=400, # 400 bad request
            detail='Item already exists'
        )
    except Exception as e:
        print(f'Error occurred: {e}')
        logging.error(traceback.format_exc())
        raise
    finally:
        await conn.close() # important: remember to await conn.close() or it'll just return the coroutine object not run it

    return successful_response

@app.post("/readings/slow/pooling")
async def post_reading_slow_pooling(reading: DatabasePayload) -> ResponseModel:
    """
    Push client request directly to PostgreSQL with connection pooling, return success
    """    
    try:
        async with app.state.pool.acquire() as conn: # main difference: use connection pool to avoid having to re-establish database connections
            async with conn.transaction(): # important: use context manager to automatically commit on cleanup
                await conn.execute('''
                    INSERT INTO readings (id, reading, timestamp)
                    VALUES ($1, $2, $3)
                ''', reading.id, reading.reading, reading.timestamp) # pass in the positional args for the sql query as separate args, not a list
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=400, # 400 bad request
            detail='Item already exists'
        )
    except Exception as e:
        print(f'Error occurred: {e}')
        logging.error(traceback.format_exc())
        raise
    finally:
        await conn.close() # important: remember to await conn.close() or it'll just return the coroutine object not run it

    return successful_response