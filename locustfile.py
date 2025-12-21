from itertools import count

import gevent
from locust import HttpUser, task
from locust.exception import StopUser

counter = count(start=1) # using global counter to update primary key in a thread safe way

class BasicConcurrentRequest(HttpUser):
    """
    Each user will make ITERATIONS number of concurrent requests to the slow/pooling API
    Global counter is used to update primary key
    """
    @task
    def send_slow_nonpool_request(self):  
        ITERATIONS = 5

        def make_request():
            i = next(counter)
            self.client.post('/readings/slow/pooling', json={'id':i, 'reading': 67})
    
        jobs = [gevent.spawn(make_request) for _ in range(ITERATIONS)] # a list of greenlet objects

        gevent.joinall(jobs) # pauses main execution to wait until jobs are finished

        raise StopUser() # one user will only make ITERATIONS number of requests