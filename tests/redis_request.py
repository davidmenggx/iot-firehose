import random
from itertools import count

from locust import FastHttpUser, task, constant

counter = count(start=1) # using global counter to update primary key id in a thread safe way

class HighThroughputUser(FastHttpUser):
    """
    Sends post request to /fast endpoint
    Increments a global counter to update primary key
    WARNING: this is not process safe when using mutiple Locust processes
    For process safe execution, use the readings2 table with the process_safe_worker and process_safe_redis_request
    Using Locust to manage greenlets instead of manually
    This prevents exhausting the number of sockets in the OS by avoiding creating new connections every time
    FastHttpUser is more CPU efficient and designed for high throughput testing
    """
    wait_time = constant(0) # make the users send requests as fast as possible

    @task
    def send_slow_nonpool_request(self):
        ENDPOINT = '/fast'
        id = next(counter)
        self.client.post(f'readings{ENDPOINT}', json={'id':id, 'reading': random.randint(0, 100)})