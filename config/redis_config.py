import redis.asyncio as redis

pool = redis.ConnectionPool.from_url('redis://localhost:6379/0', 
                                    decode_responses=True,
                                    max_connections = 200) # max_connections 200 to help handle high number of redis requests

redis_client = redis.Redis(connection_pool=pool) # create common redis client to reuse connections