from locust import FastHttpUser, task, constant

class DummyHealthRequest(FastHttpUser):
    """
    Get request to health check endpoint to test Locust RPS
    """
    wait_time = constant(0) # make the users send requests as fast as possible

    @task
    def send_slow_nonpool_request(self):
        self.client.get(f'health')