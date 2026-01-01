import random
from itertools import count

import gevent
from locust import FastHttpUser, task, constant
from locust.exception import StopUser

counter = count(start=1) # using global counter to update primary key id in a thread safe way

# important: remember to start redis worker in separate terminal using python -m workers.workers

class HighThroughputUser(FastHttpUser):
    """
    Using Locust to manage greenlets instead of manually
    FastHttpUser is more CPU efficient and designed for high throughput testing
    This prevents exhausting the number of sockets in the OS by avoiding creating new connections every time
    Global counter is used to update primary key
    """
    wait_time = constant(0) # make the users send requests as fast as possible

    @task
    def send_slow_nonpool_request(self):
        ENDPOINT = '/fast'
        id = next(counter)
        self.client.post(f'readings{ENDPOINT}', json={'id':id, 'reading': random.randint(0, 100)})