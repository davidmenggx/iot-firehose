import signal
import asyncio
import logging
from datetime import datetime
from time import time_ns

from redis import exceptions
from asyncpg.exceptions import UniqueViolationError

from config.redis_config import redis_client
from config.config import settings
from config.database_config import create_async_db_pool
from config.log import setup_logger


running: bool = True # flag to shut down worker after FastAPI shutdown

def signal_shutdown(_sig, _frame) -> None:
    """
    Stops the save_to_db loop
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
    Waits for BUFFER requests to accumulate or BUFFER_TIME second to pass
    Acquires asyncpg connection pool
    Bulk copies readings into readings2 table
    """
    try: # create consumer group if it does not already exist
        await redis_client.xgroup_create(settings.STREAM_NAME, settings.CONSUMER_GROUP, id='0', mkstream=True)
    except exceptions.ResponseError as e:
        if "Consumer Group name already exists" not in str(e): # if the exception doesn't have to do with the consumer group already existing, raise
            raise

    # create buffers
    redis_ids = [] # capture Redis auto generated IDs, e.g. 1656416957625-0.
    data = [] # capture data from each payload
    last_flush = datetime.now() # starts the timer for clearing the buffer after BUFFER_TIME seconds elapse

    pool = await create_async_db_pool(USER=settings.USER, DATABASE=settings.DATABASE,
                            HOST=settings.HOST, PORT=settings.PORT, DATABASE_PASS=settings.DATABASE_PASS,
                            MIN_SIZE=settings.MIN_SIZE, MAX_SIZE=settings.MAX_SIZE)

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
            
        if (len(redis_ids) > settings.BUFFER) or ((datetime.now() - last_flush).total_seconds() > settings.BUFFER_TIME): # clears the buffer when BUFFER capacity is hit or BUFFER_TIME is reached
            logger.debug(f'Redis group processing {len(redis_ids)} requests at time {time_ns()}')

            records = [(int(r['reading']), datetime.fromisoformat(r['timestamp'])) for r in data] # make sure data is in correct format for postgres. id is not needed since readings2 uses an identity column

            try:
                async with pool.acquire() as conn:
                    async with conn.transaction():
                            logger.debug(f'Redis group making database copy with {len(redis_ids)} requests at time {time_ns()}')
                            await conn.copy_records_to_table( 
                                'readings2',
                                records=records,
                                columns=('reading', 'timestamp') 
                            ) # uses PostgreSQL's COPY protocol, which is faster than individual inserts
                            logger.debug(f'Redis group acknowledging completing {len(redis_ids)} requests at time {time_ns()}')
                            await redis_client.xack(settings.STREAM_NAME, settings.CONSUMER_GROUP, *redis_ids) # important: acknowledges completing the task(s) to clear from pending entries list
                            
                            # clear the buffers
                            redis_ids.clear()
                            data.clear()

                            last_flush = datetime.now() # restart the BUFFER_TIME timer

                            logger.debug(f'Redis group completed processing {len(redis_ids)} requests at time {time_ns()}')
            except UniqueViolationError as e: # catches duplicate primary key errors gracefully, skipping batch instead of crashing worker
                logger.error(f'Duplicate primary key found, skipping this batch of length {len(redis_ids)}')
                print(f'Duplicate primary key found, skipping this batch of length {len(redis_ids)}')
                
                # clears the buffer to avoid retrying failed group
                redis_ids.clear()
                data.clear()
            except:
                logger.error(f'Redis group failed to process {len(redis_ids)} requests, from request ID {redis_ids[0]} to {redis_ids[-1]} at time {time_ns()}')
                raise

    print('Shutting down process safe worker')
    if settings.CLEAR_STREAM:
        await redis_client.delete(settings.STREAM_NAME) # delete the stream key if set in config

if __name__ == '__main__':
    print('Starting process safe worker')
    print('Writing to readings2 database')
    asyncio.run(save_to_db())