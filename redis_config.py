import os
from redis import Redis
from rq import Queue

redis_client = Redis(host='redis://redis:6379/0', decode_responses=True)
task_queue = Queue('task_queue', connection=redis_client)