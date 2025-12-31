import random
from itertools import count

import gevent
from locust import HttpUser, task
from locust.exception import StopUser

counter = count(start=1) # using global counter to update primary key id in a thread safe way

# important: remember to start redis worker in separate terminal using python -m workers.workers

class BasicRedisRequest(HttpUser):
    """
    Each user will make ITERATIONS number of concurrent requests to the /fast endpoint
    Global counter is used to update primary key
    """
    @task
    def send_slow_nonpool_request(self):  
        ITERATIONS = 5 # instead of creating more iterations, create more users (more iterations will hit max connection pool size in requests)
        ENDPOINT = '/fast'

        def make_request():
            id = next(counter)
            self.client.post(f'/readings{ENDPOINT}', json={'id':id, 'reading': random.randint(0, 100)})
    
        jobs = [gevent.spawn(make_request) for _ in range(ITERATIONS)] # a list of greenlet objects

        gevent.joinall(jobs) # pauses main execution to wait until jobs are finished

        raise StopUser() # one user will only make ITERATIONS number of requests