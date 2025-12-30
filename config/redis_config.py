import redis.asyncio as redis

# note: i changed the url to localhost, check if this works within the docker compose
pool = redis.ConnectionPool.from_url('redis://localhost:6379/0', 
                                    decode_responses=True,
                                    max_connections = 200)

redis_client = redis.Redis(connection_pool=pool)