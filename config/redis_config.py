from redis import Redis

STREAM_NAME = 'db_buffer'
CONSUMER_GROUP = 'workers'
CONSUMER_NAME = 'worker1'

# note: i changed the url to localhost, check if this works within the docker compose
redis_client = Redis.from_url('redis://localhost:6379/0', decode_responses=True)