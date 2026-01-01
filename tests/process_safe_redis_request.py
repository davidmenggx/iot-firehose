import random

from locust import FastHttpUser, task, constant

# important: remember to start redis worker in separate terminal using python -m workers.workers

class HighThroughputUser(FastHttpUser):
    """
    Using Locust to manage greenlets instead of manually
    This prevents exhausting the number of sockets in the OS by avoiding creating new connections every time
    FastHttpUser is more CPU efficient and designed for high throughput testing
    Since we write to the readings2 table, id field is auto generated as an identity column
    """
    wait_time = constant(0) # make the users send requests as fast as possible

    @task
    def send_slow_nonpool_request(self):
        ENDPOINT = '/fast'
        self.client.post(f'readings{ENDPOINT}', json={'id': 0, 'reading': random.randint(0, 100)}) # omit the id column since readings2 uses and identity column