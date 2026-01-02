import traceback
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from time import time_ns

from fastapi import FastAPI, HTTPException
import asyncpg

from schemas.db_model import DatabasePayload, ResponseModel
from config.redis_config import redis_client
from config.database_config import create_async_db_pool, clear_db
from config.log import setup_logger
from config.config import settings

logger: logging.Logger = setup_logger(settings.VERBOSE, settings.CLEAR_LOG)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Creates a connection pool on startup and closes on shutdown
    If CLEAR_LOG mode, clears the debug log (default False)
    If CLEAR_DB mode, clear the readings table (default False)
    If CLEAR_DB2 mode, clear the readings2 table (default False)
    Closes connection pool and redis client on shutdown
    """
    app.state.pool = await create_async_db_pool(settings.USER, settings.DATABASE, settings.HOST, settings.PORT, 
                                                settings.DATABASE_PASS, settings.MIN_SIZE, settings.MAX_SIZE) # type: ignore
    await clear_db(settings.DATABASE_PASS, settings.CLEAR_DB, settings.CLEAR_DB2)
    yield
    await app.state.pool.close()
    await redis_client.close()

app = FastAPI(lifespan=lifespan)

@app.post("/readings/fast")
async def post_reading(reading: DatabasePayload) -> ResponseModel:
    """
    Producer that xadds client request to Redis stream, return buffered
    """
    payload = {
        'id': reading.id,
        'reading': reading.reading,
        'timestamp': reading.timestamp.isoformat() # type: ignore
    } # using a dictionary payload instead of json dumping the pydantic model results in slightly less CPU usage
    
    await redis_client.xadd(settings.STREAM_NAME, payload) # type: ignore
    return ResponseModel(
        status='buffered',
        message='Item added to Redis stream',
    )

@app.post("/readings/slow/nonpooling")
async def post_reading_slow_nonpooling(reading: DatabasePayload) -> ResponseModel:
    """
    Attempts to make a connection to database without the connection pool
    Attempts to write readings directly to Postgres with asyncpg
    Closes connection
    Returns success
    """    
    try: # attempt to make a connection to database
        logger.debug(f'Request ID {reading.id} about to acquire connection at time {time_ns()}')
        conn = await asyncpg.connect(user=settings.USER, password=settings.DATABASE_PASS, 
                                database=settings.DATABASE, host=settings.HOST, port=settings.PORT)
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
    Acquires asyncpg connection pool
    Attempts to write readings directly to Postgres with asyncpg
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
            logger.debug(f'Request ID {reading.id} finalized transaction at time {time_ns()}')
        logger.debug(f'Request ID {reading.id} releasing connection at time {time_ns()}')
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

@app.get("/health")
def health_check():
    """Dummy health check endpoint"""
    return ResponseModel(
        status='success',
        message='App online'
    )

@app.get("/health/db")
async def db_health_check():
    """Dummy health check endpoint for the database connection"""
    try:
        await asyncpg.connect(user=settings.USER, password=settings.DATABASE_PASS, 
                                database=settings.DATABASE, host=settings.HOST, port=settings.PORT)
        return ResponseModel(
            status='success',
            message='Database online'
        )
    except:
        return ResponseModel(
            status='failure',
            message='Could not connect to database'
        )