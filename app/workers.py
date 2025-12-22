import signal
import io

from redis import exceptions

from config.redis_config import redis_client, STREAM_NAME, CONSUMER_GROUP, CONSUMER_NAME
from config.app_vars import USER, DATABASE, HOST, PORT, DATABASE_PASS, MIN_SIZE, MAX_SIZE, CLEAR_DB, VERBOSE, CLEAR_LOG
from config.database import create_psycopg2_db_pool
from schemas.db_model import DatabasePayload

if not DATABASE_PASS:
        raise KeyError('DATABASE_PASS not set in environment')

pool = create_psycopg2_db_pool(USER=USER, DATABASE=DATABASE, HOST=HOST, PORT=PORT, DATABASE_PASS=DATABASE_PASS, MIN_SIZE=MIN_SIZE, MAX_SIZE=MAX_SIZE)

running = True

def signal_shutdown(sig, frame):
    global running
    running = False

signal.signal(signal.SIGINT, signal_shutdown)
signal.signal(signal.SIGTERM, signal_shutdown)

def save_to_db():
    """
    Read from Redis queue and push to Postgres database
    """
    try:
        redis_client.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id='0', mkstream=True)
    except exceptions.ResponseError as e:
        if "BUSYGROUP Consumer Group name already exists" not in str(e):
            raise
    
    conn = pool.getconn()
    
    try:
        while running:
            readings = redis_client.xreadgroup(CONSUMER_GROUP, 
                                            CONSUMER_NAME, 
                                            {STREAM_NAME: '>'}, 
                                            count=1000, 
                                            block=5000)
            if not readings:
                continue

            redis_ids = []
            data = []
            for _, messages in readings: # type: ignore (PERHAPS)
                for message_id, payload in messages:
                    redis_ids.append(message_id)
                    data.append(payload)
            
            l = io.StringIO()
            for record in data:
                line = f'{record['id']}\t{record['reading']}\t{record['timestamp']}\n'
                l.write(line)
            l.seek(0)

            with conn.cursor() as cur:
                try:
                    cur.copy_from(l, 'readings', columns=('id','reading', 'timestamp'))
                    conn.commit()
                    redis_client.xack(STREAM_NAME, CONSUMER_GROUP, *redis_ids)
                except:
                    conn.rollback()
                    raise
    finally:
        pool.putconn(conn)
    print('Closing pool')
    pool.closeall()

if __name__ == '__main__':
    print('Starting worker')
    save_to_db()