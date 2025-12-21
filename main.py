import os
import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from time import time_ns

# see if i can clean this up
from fastapi import FastAPI, HTTPException
#from pydantic import BaseModel
#import redis
#from rq import Queue
import asyncpg
from dotenv import load_dotenv

from schemas.db_model import DatabasePayload, ResponseModel
from redis_config import task_queue
from app.workers import save_to_db

load_dotenv()
DATABASE_PASS = os.getenv('DATABASE_PASS')

logger = logging.getLogger(__name__)
logging.basicConfig(filename='debug.log', encoding='utf-8', level=logging.DEBUG)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Creates a connection pool on startup and closes on shutdown
    Clears the debug log
    """
    app.state.pool = await asyncpg.create_pool(user='postgres', password=DATABASE_PASS, 
                                database='iot-firehose', host='127.0.0.1', port=5432) # runs on api startup
    with open('debug.log', 'w') as file: # clears the debug log
        pass
    yield
    await app.state.pool.close() # runs on api shutdown

app = FastAPI(lifespan=lifespan)

@app.post("/readings/fast")
async def post_reading(reading: DatabasePayload) -> ResponseModel:
    """
    Push client request to Redis worker queue, return success
    """
    task_queue.enqueue(save_to_db, reading)
    return ResponseModel(
        status='success',
        message='Item created',
    )

@app.post("/readings/slow/nonpooling")
async def post_reading_slow_nonpooling(reading: DatabasePayload) -> ResponseModel:
    """
    Attempts to make a connection to database without the connection pool
    Attempts to write readings directly to Postgres
    Closes connection
    Returns success
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
        #logging.error(traceback.format_exc())
        raise
    finally:
        await conn.close() # important: remember to await conn.close() or it'll just return the coroutine object not run it

    return ResponseModel( # You need to create the ResponseModel in the coroutine so it doesn't reuse the same datetime object every time
        status='success',
        message='Item created',
        # no value for timestamp => default factory datetime
    )

@app.post("/readings/slow/pooling")
async def post_reading_slow_pooling(reading: DatabasePayload) -> ResponseModel:
    """
    Acquires the connection pool
    Attempts to write readings directly to Postgres
    Returns success
    """    
    try:
        logger.debug(f'Request ID {reading.id} about to acquire connection at time {time_ns()}')
        async with app.state.pool.acquire() as conn: # main difference: use connection pool to avoid having to re-establish database connections
            async with conn.transaction(): # important: use context manager to automatically commit on cleanup
                logger.debug(f'Request ID {reading.id} beginning execution at time {time_ns()}')
                await conn.execute('''
                    INSERT INTO readings (id, reading, timestamp)
                    VALUES ($1, $2, $3)
                ''', reading.id, reading.reading, reading.timestamp) # pass in the positional args for the sql query as separate args, not a list
                logger.debug(f'Request ID {reading.id} finished execution at time {time_ns()}')
    except asyncpg.UniqueViolationError:
        logger.error(f'Request ID {reading.id} failed to execute at time {time_ns()}: already exists')
        #logger.warning('Item with reading ID "{reading.id}" already exists')
        raise HTTPException(
            status_code=400, # 400 bad request
            detail='Item already exists'
        )
    except Exception as e:
        print(f'Error occurred: {e}')
        logger.error(f'Request ID {reading.id} failed to execute at time {time_ns()}: {traceback.format_exc()}')
        #logger.error(traceback.format_exc())
        raise
    
    logger.debug(f'Request ID {reading.id} successfully logged at time {time_ns()}')
    return ResponseModel(
        status='success',
        message='Item created',
    )