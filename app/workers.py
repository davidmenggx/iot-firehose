import signal
import io
from time import time_ns

from redis import exceptions

from config.redis_config import redis_client
from config.config import settings
from config.database import create_psycopg2_db_pool
from config.log import setup_logger

if not settings.DATABASE_PASS:
    raise KeyError('DATABASE_PASS not set in environment')

pool = create_psycopg2_db_pool(USER=settings.USER, DATABASE=settings.DATABASE, HOST=settings.HOST, PORT=settings.PORT, DATABASE_PASS=settings.DATABASE_PASS, MIN_SIZE=settings.MIN_SIZE, MAX_SIZE=settings.MAX_SIZE) # type: ignore

running = True # flag to shut down worker after FastAPI shutdown

def signal_shutdown(sig, frame) -> None:
    """
    Stops the save_to_db worker
    """
    global running
    running = False

signal.signal(signal.SIGINT, signal_shutdown)
signal.signal(signal.SIGTERM, signal_shutdown)

logger = setup_logger(settings.VERBOSE, settings.CLEAR_LOG)

def save_to_db() -> None:
    """
    Read from Redis stream
    Returns a maximum of 1000 requests at a time
    Waits 5 seconds if no messages have been added to the stream
    Acquires psycopg2 connection pool
    Bulk copies readings into PostgreSQL database
    """
    try: # create consumer group if it does not already exist
        redis_client.xgroup_create(settings.STREAM_NAME, settings.CONSUMER_GROUP, id='0', mkstream=True)
    except exceptions.ResponseError as e:
        if "Consumer Group name already exists" not in str(e):
            raise
        
    while running: # worker loop
        readings = redis_client.xreadgroup(settings.CONSUMER_GROUP, 
                                        settings.CONSUMER_NAME, 
                                        {settings.STREAM_NAME: '>'}, # '>' meaning: look it up
                                        count=1000, 
                                        block=5000)
        if not readings:
            continue

        conn = pool.getconn()

        redis_ids = [] 
        data = []
        # collect all of the readings and separate out redis ids (for acknowledgement) from data (for processing)
        for _, messages in readings: # type: ignore
            for message_id, payload in messages:
                redis_ids.append(message_id)
                data.append(payload)
            
        if redis_ids:
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
                redis_client.xack(settings.STREAM_NAME, settings.CONSUMER_GROUP, *redis_ids) # important: you need to acknowledge completing the task to clear from pending entries list
                logger.debug(f'Redis group completed processing {len(redis_ids)} requests at time {time_ns()}')
            except:
                conn.rollback()
                logger.error(f'Redis group failed to process {len(redis_ids)} requests, from request ID {redis_ids[0]} to {redis_ids[-1]} at time {time_ns()}')
                raise
            finally:
                pool.putconn(conn)
    print('Shutting down worker')
    if settings.CLEAR_STREAM:
        redis_client.delete(settings.STREAM_NAME)

if __name__ == '__main__':
    print('Starting worker')
    save_to_db()