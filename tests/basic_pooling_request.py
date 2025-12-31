from itertools import count

import gevent
from locust import HttpUser, task
from locust.exception import StopUser

counter = count(start=1) # using global counter to update primary key id in a thread safe way

class BasicConcurrentRequest(HttpUser):
    """
    Each user will make ITERATIONS number of concurrent requests to the /slow/pooling endpoint
    Global counter is used to update primary key
    """
    pool_maxsize = 50

    @task
    def send_slow_nonpool_request(self):  
        ITERATIONS = 5
        ENDPOINT = '/slow/pooling'

        def make_request():
            id = next(counter)
            self.client.post(f'/readings{ENDPOINT}', json={'id':id, 'reading': 67})
    
        jobs = [gevent.spawn(make_request) for _ in range(ITERATIONS)] # a list of greenlet objects

        gevent.joinall(jobs) # pauses main execution to wait until jobs are finished

        raise StopUser() # one user will only make ITERATIONS number of requests