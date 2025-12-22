import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from time import time_ns

from fastapi import FastAPI, HTTPException
import asyncpg

from schemas.db_model import DatabasePayload, ResponseModel
from config.redis_config import redis_client, STREAM_NAME
from config.database import create_async_db_pool, clear_db
from config.log import setup_logger
from config.app_vars import USER, DATABASE, HOST, PORT, DATABASE_PASS, MIN_SIZE, MAX_SIZE, CLEAR_DB, VERBOSE, CLEAR_LOG

logger = setup_logger(VERBOSE, CLEAR_LOG)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Creates a connection pool on startup and closes on shutdown
    If CLEAR_LOG mode, clears the debug log (default false)
    If CLEAR_DB mode, clear the Postgres database (default false)
    """
    if not DATABASE_PASS:
        raise KeyError('DATABASE_PASS not set in environment')

    app.state.pool = await create_async_db_pool(USER, DATABASE, HOST, PORT, DATABASE_PASS, MIN_SIZE, MAX_SIZE)

    await clear_db(DATABASE_PASS, CLEAR_DB)
    yield
    await app.state.pool.close()

app = FastAPI(lifespan=lifespan)

@app.post("/readings/fast")
async def post_reading(reading: DatabasePayload) -> ResponseModel:
    """
    Push client request to Redis worker queue, return success
    """
    redis_client.xadd(STREAM_NAME, reading.model_dump(mode='json')) # type: ignore
    return ResponseModel(
        status='buffered',
        message='Item sent to Redis buffer',
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
        logger.debug(f'Request ID {reading.id} about to acquire connection at time {time_ns()}')
        conn = await asyncpg.connect(user='postgres', password=DATABASE_PASS, 
                                database='iot-firehose', host='127.0.0.1', port=5432)
    except Exception as e:
        logger.error(f'Request ID {reading.id} failed to connect to database at time {time_ns()}')
        raise HTTPException(
            status_code=500,
            detail='Could not connect to database'
        )

    try:
        async with conn.transaction(): # important: use context manager to automatically commit on cleanup
            logger.debug(f'Request ID {reading.id} beginning execution at time {time_ns()}')
            await conn.execute('''
                INSERT INTO readings (id, reading, timestamp)
                VALUES ($1, $2, $3)
            ''', reading.id, reading.reading, reading.timestamp) # pass in the positional args for the sql query as separate args, not a list
            logger.debug(f'Request ID {reading.id} finished execution at time {time_ns()}')
    except asyncpg.UniqueViolationError:
        logger.error(f'Request ID {reading.id} failed to execute at time {time_ns()}: already exists')
        raise HTTPException(
            status_code=400, # 400 bad request
            detail='Item already exists'
        )
    except Exception as e:
        print(f'Error occurred: {e}')
        logger.error(f'Request ID {reading.id} failed to execute at time {time_ns()}: {traceback.format_exc()}')
        raise
    finally:
        logger.debug(f'Request ID {reading.id} closing connection at time {time_ns()}')
        await conn.close() # important: remember to await conn.close() or it'll just return the coroutine object not run it

    logger.debug(f'Request ID {reading.id} successfully logged at time {time_ns()}')
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
        raise HTTPException(
            status_code=400, # 400 bad request
            detail='Item already exists'
        )
    except Exception as e:
        print(f'Error occurred: {e}')
        logger.error(f'Request ID {reading.id} failed to execute at time {time_ns()}: {traceback.format_exc()}')
        raise
    
    logger.debug(f'Request ID {reading.id} successfully logged at time {time_ns()}')
    return ResponseModel(
        status='success',
        message='Item created',
    )