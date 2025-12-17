import os
import redis

redis_client = redis.Redis(host='redis://redis:6379/0', decode_responses=True)