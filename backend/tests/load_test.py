"""
Load testing for clip generation pipeline.
Simulates 100+ concurrent moments and validates system stability under stress.

Run with: locust -f backend/tests/load_test.py --host=http://localhost:8000
Or for Railway: locust -f backend/tests/load_test.py --host=https://your-railway-domain.com
"""

import random
import time
from locust import HttpUser, task, between, events
from datetime import datetime, timezone


class ClipPipelineLoadTest(HttpUser):
    """Simulate concurrent clip creation and management operations"""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Initialize test user before starting tasks"""
        self.token = None
        self.streamer_id = 1
        self.auth_header = {}
        self.login()

    def login(self):
        """Authenticate and get session token"""
        try:
            response = self.client.post(
                "/auth/login",
                json={
                    "username": "testuser",
                    "password": "testpass123"
                },
                name="POST /auth/login"
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.auth_header = {"Authorization": f"Bearer {self.token}"}
        except Exception as e:
            print(f"Login failed: {e}")

    @task(5)
    def detect_moment(self):
        """Simulate moment detection - MOST FREQUENT (5x weight)"""
        moment_data = {
            "stream_id": "test_stream_123",
            "moment_id": f"moment_{int(time.time() * 1000)}_{random.randint(0, 9999)}",
            "timestamp": int(time.time()),
            "chat_events": random.randint(50, 500),
            "emote_rate": random.uniform(0.1, 0.9),
            "caps_ratio": random.uniform(0.1, 0.7),
        }

        with self.client.post(
            "/moments/detect",
            json=moment_data,
            headers=self.auth_header,
            catch_response=True,
            name="POST /moments/detect"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(2)
    def list_pending_clips(self):
        """List pending clips - FREQUENT (2x weight)"""
        with self.client.get(
            "/api/clips/pending",
            headers=self.auth_header,
            catch_response=True,
            name="GET /api/clips/pending"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "clips" in data:
                    response.success()
                else:
                    response.failure("Invalid response format")
            else:
                response.failure(f"Status {response.status_code}")

    @task(2)
    def check_clips_generated(self):
        """Check generated clips - FREQUENT (2x weight)"""
        with self.client.get(
            "/api/clips/check-generated",
            headers=self.auth_header,
            catch_response=True,
            name="GET /api/clips/check-generated"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(1)
    def approve_clip(self):
        """Approve a pending clip - OCCASIONAL (1x weight)"""
        with self.client.get(
            "/api/clips/pending",
            headers=self.auth_header,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                clips = response.json().get("clips", [])
                if clips:
                    clip_id = clips[0]["id"]

                    with self.client.post(
                        "/api/clips/review",
                        json={"clip_id": clip_id, "action": "approve"},
                        headers=self.auth_header,
                        catch_response=True,
                        name="POST /api/clips/review (approve)"
                    ) as review_response:
                        if review_response.status_code == 200:
                            review_response.success()
                        else:
                            review_response.failure(f"Status {review_response.status_code}")

    @task(1)
    def reject_clip(self):
        """Reject a pending clip - OCCASIONAL (1x weight)"""
        with self.client.get(
            "/api/clips/pending",
            headers=self.auth_header,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                clips = response.json().get("clips", [])
                if clips:
                    clip_id = clips[0]["id"]

                    with self.client.post(
                        "/api/clips/review",
                        json={"clip_id": clip_id, "action": "reject"},
                        headers=self.auth_header,
                        catch_response=True,
                        name="POST /api/clips/review (reject)"
                    ) as review_response:
                        if review_response.status_code == 200:
                            review_response.success()
                        else:
                            review_response.failure(f"Status {review_response.status_code}")

    @task(1)
    def get_storage_stats(self):
        """Get storage statistics - OCCASIONAL (1x weight)"""
        with self.client.get(
            "/api/clips/storage/stats",
            headers=self.auth_header,
            catch_response=True,
            name="GET /api/clips/storage/stats"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "total_files" in data:
                    response.success()
                else:
                    response.failure("Invalid response format")
            else:
                response.failure(f"Status {response.status_code}")

    @task(1)
    def get_monitoring_stats(self):
        """Get monitoring stats - OCCASIONAL (1x weight)"""
        with self.client.get(
            "/api/monitoring/stats",
            headers=self.auth_header,
            catch_response=True,
            name="GET /api/monitoring/stats"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "clip_pipeline" in data:
                    response.success()
                else:
                    response.failure("Invalid response format")
            else:
                response.failure(f"Status {response.status_code}")


class StressTestUser(HttpUser):
    """Aggressive stress testing with minimal wait times"""

    wait_time = between(0.5, 1)  # Minimal wait

    def on_start(self):
        """Initialize before stress test"""
        self.token = None
        self.auth_header = {}
        self.login()

    def login(self):
        """Authenticate"""
        try:
            response = self.client.post(
                "/auth/login",
                json={
                    "username": "testuser",
                    "password": "testpass123"
                }
            )
            if response.status_code == 200:
                self.token = response.json().get("token")
                self.auth_header = {"Authorization": f"Bearer {self.token}"}
        except:
            pass

    @task
    def rapid_moment_detection(self):
        """Rapid-fire moment detection"""
        moment_data = {
            "stream_id": "stress_test",
            "moment_id": f"stress_{int(time.time() * 1000000)}",
            "timestamp": int(time.time()),
            "chat_events": random.randint(10, 100),
            "emote_rate": random.uniform(0.05, 0.5),
            "caps_ratio": random.uniform(0.05, 0.3),
        }

        self.client.post(
            "/moments/detect",
            json=moment_data,
            headers=self.auth_header,
            catch_response=True
        )


# Event handlers for reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("\n" + "=" * 60)
    print("🚀 LOAD TEST STARTED")
    print("=" * 60)
    print(f"Target: {environment.host}")
    print(f"Start time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("\n" + "=" * 60)
    print("✅ LOAD TEST COMPLETED")
    print("=" * 60)
    print(f"End time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time:.0f}ms")
    print(f"95th percentile: {environment.stats.total.get_response_time_percentile(0.95):.0f}ms")
    print(f"99th percentile: {environment.stats.total.get_response_time_percentile(0.99):.0f}ms")
    print("=" * 60 + "\n")


# Test scenarios
"""
Run different load test scenarios:

1. NORMAL LOAD (gradual ramp-up):
   locust -f backend/tests/load_test.py \\
     --host=http://localhost:8000 \\
     -u 100 \\
     -r 10 \\
     -t 5m

   -u 100: 100 concurrent users
   -r 10: Spawn 10 new users per second
   -t 5m: Run for 5 minutes

2. STRESS TEST (aggressive):
   locust -f backend/tests/load_test.py \\
     --host=http://localhost:8000 \\
     -u 500 \\
     -r 50 \\
     -t 10m

   -u 500: 500 concurrent users
   -r 50: Spawn 50 new users per second
   -t 10m: Run for 10 minutes

3. SPIKE TEST (sudden traffic):
   locust -f backend/tests/load_test.py \\
     --host=http://localhost:8000 \\
     -u 1000 \\
     -r 100 \\
     -t 5m

   -u 1000: 1000 concurrent users
   -r 100: Spawn 100 new users per second
   -t 5m: Run for 5 minutes

4. HEADLESS (CI/CD):
   locust -f backend/tests/load_test.py \\
     --host=http://localhost:8000 \\
     -u 100 -r 10 -t 5m \\
     --headless \\
     -c 4 \\
     --csv=results

   --headless: No web UI
   -c 4: Use 4 cores
   --csv=results: Export results to CSV

5. WEB UI (interactive):
   locust -f backend/tests/load_test.py \\
     --host=http://localhost:8000

   Then open http://localhost:8089
"""

"""
Expected Metrics at 100 concurrent users:
- Response time: <200ms (95th percentile)
- Success rate: >99%
- Errors: <1%
- RPS: >50 requests/second

Critical thresholds:
- If p95 > 1000ms: Performance degradation
- If error rate > 5%: Potential bottleneck
- If p99 > 5000ms: System struggling
"""
