from locust import FastHttpUser, task, constant

class DummyHealthRequest(FastHttpUser):
    """
    Dummy request to health check endpoint for testing purposes
    FastHttpUser is more CPU efficient and designed for high throughput testing
    """
    wait_time = constant(0) # make the users send requests as fast as possible

    @task
    def send_slow_nonpool_request(self):
        self.client.get(f'health')