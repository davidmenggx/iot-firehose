from redis import Redis

STREAM_NAME = 'db_buffer'
CONSUMER_GROUP = 'workers'
CONSUMER_NAME = 'worker1'

redis_client = Redis.from_url('redis://localhost:6379/0', decode_responses=True)