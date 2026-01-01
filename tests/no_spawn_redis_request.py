import random
from itertools import count

from locust import HttpUser, task

counter = count(start=1) # using global counter to update primary key id in a thread safe way

# important: remember to start redis worker in separate terminal using python -m workers.workers

class BasicRedisRequest(HttpUser):
    """
    Using Locust to manage greenlets instead of manually
    This prevents exhausting the number of sockets in the OS by avoiding creating new connections every time
    Global counter is used to update primary key
    """
    @task
    def send_slow_nonpool_request(self):
        ENDPOINT = '/fast'
        id = next(counter)
        self.client.post(f'/readings{ENDPOINT}', json={'id':id, 'reading': random.randint(0, 100)})