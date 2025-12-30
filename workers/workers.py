import signal
import asyncio
import io
import logging
from datetime import datetime
from time import time_ns

from psycopg2.pool import ThreadedConnectionPool
from redis import exceptions

from config.redis_config import redis_client
from config.config import settings
from config.database_config import create_psycopg2_db_pool
from config.log import setup_logger

pool: ThreadedConnectionPool = create_psycopg2_db_pool(USER=settings.USER, DATABASE=settings.DATABASE, 
                                                                    HOST=settings.HOST, PORT=settings.PORT, 
                                                                    DATABASE_PASS=settings.DATABASE_PASS, MIN_SIZE=settings.MIN_SIZE, 
                                                                    MAX_SIZE=settings.MAX_SIZE) # type: ignore

running: bool = True # flag to shut down worker after FastAPI shutdown

def signal_shutdown(_sig, _frame) -> None:
    """
    Stops the save_to_db worker
    _sig and _frame are required by the signal module
    """
    global running
    running = False

signal.signal(signal.SIGINT, signal_shutdown) # Catch CTRL+C
signal.signal(signal.SIGTERM, signal_shutdown) # Catch kill command

logger: logging.Logger = setup_logger(settings.VERBOSE, settings.CLEAR_LOG)

async def save_to_db() -> None:
    """
    Read from Redis stream
    Returns a maximum of 1000 requests at a time
    Waits 5 seconds if no messages have been added to the stream
    Acquires psycopg2 connection pool
    Bulk copies readings into PostgreSQL database
    """
    try: # create consumer group if it does not already exist
        await redis_client.xgroup_create(settings.STREAM_NAME, settings.CONSUMER_GROUP, id='0', mkstream=True)
    except exceptions.ResponseError as e:
        if "Consumer Group name already exists" not in str(e): # if the exception doesn't have to do with the consumer group already existing, raise
            raise

    redis_ids = [] # capture Redis auto generated IDs, e.g. 1656416957625-0.
    data = [] 
    last_flush = datetime.now()

    while running: # worker loop
        readings = await redis_client.xreadgroup(settings.CONSUMER_GROUP, 
                                        settings.CONSUMER_NAME, 
                                        {settings.STREAM_NAME: '>'}, # '>' means worker only reads from latest messages in the stream and adds to PEL util xack
                                        count=1000, # read up to 1000 messages at a time
                                        block=5000) # worker will wait for messages for up to 5 seconds before returning empty
        if not readings:
            continue

        
        # collect all of the readings and separate out redis ids (for acknowledgement) from data (for processing)
        for _, messages in readings: # type: ignore
            for message_id, payload in messages:
                redis_ids.append(message_id)
                data.append(payload)
            
        if (len(redis_ids) > settings.BUFFER) or ((datetime.now() - last_flush).total_seconds() > 1):
            conn = pool.getconn()
            logger.debug(f'Redis group processing {len(redis_ids)} requests at time {time_ns()}')
            
            l = io.StringIO() # this is required to use the cursor.copy_from method
            for record in data:
                line = f'{record['id']}\t{record['reading']}\t{record['timestamp']}\n' # format the readings into distinct fields, one on each row
                l.write(line)
            l.seek(0)

            with conn.cursor() as cur:
                try:
                    cur.copy_from(l, 'readings', columns=('id','reading', 'timestamp')) # bulk enters the data into Postgres
                    conn.commit()
                    await redis_client.xack(settings.STREAM_NAME, settings.CONSUMER_GROUP, *redis_ids) # important: you need to acknowledge completing the task to clear from pending entries list
                    
                    redis_ids.clear()
                    data.clear()
                    last_flush = datetime.now()
                    logger.debug(f'Redis group completed processing {len(redis_ids)} requests at time {time_ns()}')
                except:
                    conn.rollback()
                    logger.error(f'Redis group failed to process {len(redis_ids)} requests, from request ID {redis_ids[0]} to {redis_ids[-1]} at time {time_ns()}')
                    raise
                finally:
                    pool.putconn(conn)
    print('Shutting down worker')
    if settings.CLEAR_STREAM:
        await redis_client.delete(settings.STREAM_NAME) # delete the stream key if set in config

if __name__ == '__main__':
    print('Starting worker')
    asyncio.run(save_to_db())