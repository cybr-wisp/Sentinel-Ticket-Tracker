
from locust import HttpUser, task, between

class SentinelUser(HttpUser):
    wait_time = between(1, 3)   # each simulated user pauses 1-3s between actions

    @task(3)                    # weight 3: hit this 3x as often
    def api_root(self):
        self.client.get("/api/")

    @task(1)
    def tickets_list(self):
        # anonymous → 401; that's fine, we're measuring latency, not success
        self.client.get("/api/tickets/")