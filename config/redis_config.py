from redis import Redis

# note: i changed the url to localhost, check if this works within the docker compose
redis_client = Redis.from_url('redis://localhost:6379/0', decode_responses=True)