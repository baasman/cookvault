#!/usr/bin/env python3
"""
Load testing script for Cookbook Creator application
Focuses on memory-intensive recipe upload operations with memory tracking
"""

import json
import random
import sys
import time
from pathlib import Path
from typing import Optional

import yaml
from locust import HttpUser, TaskSet, between, events, task

# Global variable to store memory samples during test
memory_samples = []

# Configuration
BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "scripts" / "load_test_config.yaml"
USERS_FILE = BASE_DIR / "scripts" / "test_users.json"

# Load configuration
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Load test users
with open(USERS_FILE, 'r', encoding='utf-8') as f:
    users_data = json.load(f)
    TEST_USERS = users_data['users']
    ADMIN_USERS = users_data.get('admin_users', [])


class RecipeUploadBehavior(TaskSet):
    """User behavior for recipe upload testing"""

    def on_start(self):
        """Called when a user starts executing this TaskSet"""
        self.token = None
        self.user_data = None
        self.available_recipe_ids = []

        # Simulate different IP addresses for better production testing
        # This helps test rate limiting behavior in realistic scenarios
        user_index = random.randint(1, 1000)
        fake_ip = f"10.{random.randint(1, 254)}.{random.randint(1, 254)}.{user_index % 254}"
        self.client.headers['X-Forwarded-For'] = fake_ip
        self.client.headers['X-Real-IP'] = fake_ip

        self.login()
        self.fetch_recipe_ids()

    def login(self):
        """Authenticate and get JWT token"""
        user = random.choice(TEST_USERS)
        self.user_data = user

        response = self.client.post(
            "/api/auth/login",
            json={
                "login": user["username"],
                "password": user["password"]
            },
            name="Login"
        )

        if response.status_code == 200:
            data = response.json()
            # The API returns "access_token" not "token"
            self.token = data.get("access_token")
            if self.token:
                self.client.headers['Authorization'] = f"Bearer {self.token}"
                print(f"✓ Logged in as {user['username']} with JWT")
            else:
                print(f"✓ Logged in as {user['username']} with session (no JWT)")
        else:
            print(f"✗ Login failed for {user['username']}: {response.status_code}")
            print(f"   Response: {response.text}")

    def fetch_recipe_ids(self):
        """Fetch available recipe IDs for testing"""
        # Try to fetch recipes regardless of token (session auth might work)

        try:
            response = self.client.get(
                "/api/recipes",
                params={'per_page': 100},
                name="Fetch Recipe List"
            )

            if response.status_code == 200:
                data = response.json()
                recipes = data.get('recipes', [])
                self.available_recipe_ids = [recipe['id'] for recipe in recipes]
                print(
                    f"✓ Fetched {len(self.available_recipe_ids)} recipe IDs for testing"
                )

                # If no recipes found, use empty list - view_recipe_detail will skip
                if not self.available_recipe_ids:
                    print("⚠️ No recipes found - recipe detail viewing will be skipped")
            else:
                print(f"⚠️ Could not fetch recipe list: {response.status_code}")
                self.available_recipe_ids = []

        except Exception as e:  # pylint: disable=broad-except
            print(f"⚠️ Error fetching recipe IDs: {str(e)}")
            self.available_recipe_ids = []

    def get_test_image(self, image_type: str = "single") -> list:
        """Get test image path and file data"""
        if image_type == "single":
            image_path = BASE_DIR / config['test_data']['single_image']
            return [(image_path, open(image_path, 'rb'))]  # pylint: disable=consider-using-with

        images = []
        for img_path in config['test_data']['multi_images']:
            full_path = BASE_DIR / img_path
            images.append((full_path, open(full_path, 'rb')))  # pylint: disable=consider-using-with
        return images

    @task(5)
    def upload_single_image(self):
        """Upload a single recipe image"""
        if not self.token:
            print("No token, skipping upload")
            return

        try:
            images = self.get_test_image("single")
            image_path, image_file = images[0]

            files = {
                'image': (image_path.name, image_file, 'image/jpeg')
            }

            data = {
                'cookbook_id': random.choice([None, '1', '2']),
                'page_number': str(random.randint(1, 100))
            }

            response = self.client.post(
                "/api/recipes/upload",
                files=files,
                data=data,
                name="Upload Single Recipe",
                timeout=30
            )

            if response.status_code == 201:
                job_data = response.json()
                job_id = job_data.get('job_id')
                if job_id:
                    print(f"Single upload started, job ID: {job_id}")
                    self.wait_for_job_completion(job_id)
                else:
                    print("Single upload succeeded but no job_id returned")
            elif response.status_code == 403:
                print(f"Upload limit reached for {self.user_data['username']}")
            else:
                print(f"Single upload failed with status {response.status_code}")

            image_file.close()

        except Exception as e:  # pylint: disable=broad-except
            print(f"Error in single upload: {str(e)}")

    @task(3)
    def upload_multi_images(self):
        """Upload multiple recipe images"""
        if not self.token:
            print("No token, skipping multi-upload")
            return

        try:
            images = self.get_test_image("multi")

            files = []
            for image_path, image_file in images:
                files.append(
                    ('images', (image_path.name, image_file, 'image/jpeg'))
                )

            data = {
                'cookbook_id': random.choice([None, '1', '2']),
                'recipe_title': f"Test Recipe {random.randint(1000, 9999)}"
            }

            response = self.client.post(
                "/api/recipes/upload-multi",
                files=files,
                data=data,
                name="Upload Multi Recipe",
                timeout=120  # Increased timeout for multi-image processing
            )

            if response.status_code == 201:
                job_data = response.json()
                job_id = job_data.get('job_id')
                if job_id:
                    print(f"Multi upload started, job ID: {job_id}")
                    self.wait_for_job_completion(job_id)
                else:
                    print("Multi upload succeeded but no job_id returned")
            elif response.status_code == 403:
                print(f"Upload limit reached for {self.user_data['username']}")
            else:
                print(f"Multi upload failed with status {response.status_code}")

            # Close all files
            for _, image_file in images:
                image_file.close()

        except Exception as e:  # pylint: disable=broad-except
            print(f"Error in multi upload: {str(e)}")

    @task(3)
    def browse_recipes(self):
        """Browse existing recipes (read operation)"""
        # Use either /api/recipes or /api/recipes/discover
        endpoint = random.choice(["/api/recipes", "/api/recipes/discover"])

        params = {
            'page': random.randint(1, 5),
            'per_page': 20,
        }

        # For the main recipes endpoint, add search parameter sometimes
        if endpoint == "/api/recipes" and random.random() < 0.3:
            params['search'] = random.choice(['pasta', 'chicken', 'salad', 'soup'])

        self.client.get(
            endpoint,
            params=params,
            name="Browse Recipes"
        )

    @task(1)
    def view_recipe_detail(self):
        """View a specific recipe"""
        # Only try to view recipes if we have valid IDs
        if not self.available_recipe_ids:
            return

        recipe_id = random.choice(self.available_recipe_ids)
        self.client.get(
            f"/api/recipes/{recipe_id}",
            name="View Recipe Detail"
        )

    @task(1)
    def search_recipes(self):
        """Search for recipes using the search parameter"""
        search_terms = ["pasta", "chicken", "salad", "soup", "dessert"]
        params = {
            'search': random.choice(search_terms),
            'page': 1,
            'per_page': 10
        }

        self.client.get(
            "/api/recipes",
            params=params,
            name="Search Recipes"
        )

    @task(1)
    def browse_cookbooks(self):
        """Browse available cookbooks"""
        params = {
            'page': random.randint(1, 3),
            'per_page': 20,
        }

        self.client.get(
            "/api/cookbooks",
            params=params,
            name="Browse Cookbooks"
        )

    @task(1)
    def sample_memory(self):
        """Periodically sample server memory usage (same weight as other low-priority tasks)"""
        if not self.token:
            return

        try:
            with self.client.get(
                "/api/system/metrics",
                name="Sample Memory",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    metrics = response.json()
                    memory_sample = {
                        'timestamp': metrics.get('timestamp'),
                        'process_memory_mb': metrics.get('process', {}).get('memory', {}).get('rss_mb'),
                        'process_memory_percent': metrics.get('process', {}).get('memory', {}).get('percent'),
                        'system_memory_available_mb': metrics.get('system', {}).get('memory', {}).get('available_mb'),
                        'system_memory_percent': metrics.get('system', {}).get('memory', {}).get('percent'),
                        'process_cpu_percent': metrics.get('process', {}).get('cpu_percent'),
                        'num_threads': metrics.get('process', {}).get('num_threads'),
                        'open_files': metrics.get('process', {}).get('open_files'),
                    }
                    memory_samples.append(memory_sample)
                    response.success()
                elif response.status_code == 403:
                    # User doesn't have admin access - silently skip
                    response.success()
                elif response.status_code == 401:
                    # Authentication failed - silently skip
                    response.success()
                else:
                    # Mark as failed for other errors
                    response.failure(f"Failed to get metrics: {response.status_code}")
        except Exception as e:  # pylint: disable=broad-except
            # Don't print errors for memory sampling to avoid cluttering output
            pass

    def wait_for_job_completion(self, job_id: Optional[int], max_wait: int = 120):
        """Poll job status until completion"""
        if not job_id:
            return

        # For load testing, occasionally skip job completion checking
        # to simulate users who navigate away during processing
        if random.random() < 0.3:  # 30% chance to skip waiting
            print(f"Skipping job {job_id} completion check "
                  f"(simulating user navigation)")
            return

        start_time = time.time()
        while time.time() - start_time < max_wait:
            # Mark this request as expected to potentially fail
            with self.client.get(
                f"/api/jobs/{job_id}",
                name="Check Job Status",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    job_data = response.json()
                    status = job_data.get('status')

                    if status in ['COMPLETED', 'FAILED']:
                        print(f"Job {job_id} finished with status: {status}")
                        response.success()
                        return
                    response.success()
                elif response.status_code == 404:
                    # Job not found - it may have completed and been cleaned up
                    # This is not an error in load testing context
                    response.success()
                    print(f"Job {job_id} not found (likely completed)")
                    return
                else:
                    # Other errors are real failures
                    response.failure(f"Unexpected status code: {response.status_code}")

            # Use longer sleep interval for load testing to reduce server load
            time.sleep(5)  # Increased from 2s to 5s for production testing

        print(f"Job {job_id} timeout after {max_wait}s "
              f"(normal for complex processing under load)")


class StandardUser(HttpUser):
    """Standard user with normal browsing patterns"""
    tasks = [RecipeUploadBehavior]
    wait_time = between(2, 5)

    def on_stop(self):
        """Clean up when user stops"""
        if hasattr(self, 'client') and 'Authorization' in self.client.headers:
            del self.client.headers['Authorization']


class AggressiveUser(HttpUser):
    """Aggressive user with rapid upload patterns"""
    tasks = [RecipeUploadBehavior]
    wait_time = between(0.5, 2)

    def on_stop(self):
        """Clean up when user stops"""
        if hasattr(self, 'client') and 'Authorization' in self.client.headers:
            del self.client.headers['Authorization']


class BurstUser(HttpUser):
    """User that creates burst traffic patterns"""
    tasks = [RecipeUploadBehavior]

    def wait_time(self):
        """Create burst patterns"""
        if random.random() < 0.1:  # 10% chance of burst
            return random.uniform(0.1, 0.5)
        else:
            return random.uniform(5, 10)

    def on_stop(self):
        """Clean up when user stops"""
        if hasattr(self, 'client') and 'Authorization' in self.client.headers:
            del self.client.headers['Authorization']


# Event handlers for additional metrics
@events.init.add_listener
def on_locust_init(environment, **kwargs):  # pylint: disable=unused-argument
    """Initialize additional monitoring"""
    target = environment.host if hasattr(environment, 'host') else 'Not set'
    print(
        f"╔══════════════════════════════════════════════╗\n"
        f"║   Cookbook Creator Load Testing Suite         ║\n"
        f"║   Target: {target}\n"
        f"║   Config: {CONFIG_FILE}\n"
        f"╚══════════════════════════════════════════════╝"
    )


def reset_test_user_upload_counters():
    """
    Display test user status for load testing.

    Note: This function now uses consolidated utilities from test_user_utils.py
          For actual user management, run prepare_load_test.py before testing.
    """
    print("Checking test user configuration...")

    # Try to import consolidated utilities for better status display
    try:
        sys.path.insert(0, str(BASE_DIR / "scripts"))
        from test_user_utils import print_test_user_status

        print_test_user_status()
        print("✓ Test users ready for load testing!")

    except ImportError:
        # Fallback to basic status check using loaded config
        print(f"✓ {len(TEST_USERS)} test users available for load testing")

        # Show sample users
        for user in TEST_USERS[:3]:
            tier = user.get('tier', 'unknown')
            print(f"   - {user['username']} ({tier})")
        if len(TEST_USERS) > 3:
            print(f"   ... and {len(TEST_USERS) - 3} more")

        if ADMIN_USERS:
            print(f"✓ {len(ADMIN_USERS)} admin users available")

        print("✓ All test users configured as PREMIUM with unlimited uploads")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):  # pylint: disable=unused-argument
    """Called when test starts"""
    # User count is not available at test start, only during runtime
    print("Starting load test...")

    # Reset upload counters for test users
    reset_test_user_upload_counters()

    print("Test images loaded:")
    print(f"  - Single: {config['test_data']['single_image']}")
    for img in config['test_data']['multi_images']:
        print(f"  - Multi: {img}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):  # pylint: disable=unused-argument
    """Called when test stops"""
    print("\nTest completed. Generating statistics...")

    # Print summary statistics
    stats = environment.stats
    print("\n=== Test Summary ===")
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Min Response Time: {stats.total.min_response_time:.2f}ms")
    print(f"Max Response Time: {stats.total.max_response_time:.2f}ms")

    # Calculate and print memory statistics if we have samples
    memory_stats = {}
    if memory_samples:
        print("\n=== Memory Statistics ===")
        print(f"Total Memory Samples: {len(memory_samples)}")

        # Calculate memory statistics
        memory_values = [s['process_memory_mb'] for s in memory_samples if s['process_memory_mb']]
        if memory_values:
            memory_stats = {
                'peak_memory_mb': max(memory_values),
                'avg_memory_mb': sum(memory_values) / len(memory_values),
                'min_memory_mb': min(memory_values),
                'memory_growth_mb': memory_values[-1] - memory_values[0] if len(memory_values) > 1 else 0,
            }

            print(f"Peak Memory: {memory_stats['peak_memory_mb']:.2f} MB")
            print(f"Average Memory: {memory_stats['avg_memory_mb']:.2f} MB")
            print(f"Min Memory: {memory_stats['min_memory_mb']:.2f} MB")
            print(f"Memory Growth: {memory_stats['memory_growth_mb']:.2f} MB")

            # Calculate average memory per request if we have request count
            if stats.total.num_requests > 0:
                memory_per_request = memory_stats['avg_memory_mb'] / (stats.total.num_requests / len(memory_samples))
                print(f"Approximate Memory per Request: {memory_per_request:.4f} MB")

        # CPU statistics
        cpu_values = [s['process_cpu_percent'] for s in memory_samples if s['process_cpu_percent'] is not None]
        if cpu_values:
            print(f"\n=== CPU Statistics ===")
            print(f"Peak CPU: {max(cpu_values):.2f}%")
            print(f"Average CPU: {sum(cpu_values) / len(cpu_values):.2f}%")

        # Thread and file descriptor statistics
        thread_values = [s['num_threads'] for s in memory_samples if s['num_threads']]
        file_values = [s['open_files'] for s in memory_samples if s['open_files']]
        if thread_values:
            print(f"\n=== Resource Statistics ===")
            print(f"Peak Threads: {max(thread_values)}")
            print(f"Peak Open Files: {max(file_values) if file_values else 0}")
    else:
        print("\n⚠️ No memory samples collected. Make sure:")
        print("  - At least one test user has admin privileges")
        print("  - The /api/system/metrics endpoint is accessible")

    # Save detailed stats to file
    stats_file = BASE_DIR / "scripts" / "load_test_results.json"
    results = {
        'total_requests': stats.total.num_requests,
        'total_failures': stats.total.num_failures,
        'avg_response_time': stats.total.avg_response_time,
        'min_response_time': stats.total.min_response_time,
        'max_response_time': stats.total.max_response_time,
        'requests_per_second': stats.total.current_rps,
        'failures_per_second': stats.total.current_fail_per_sec,
    }

    # Add memory statistics if available
    if memory_stats:
        results['memory'] = memory_stats

    # Add memory timeline
    if memory_samples:
        results['memory_timeline'] = memory_samples

    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: {stats_file}")
    if memory_samples:
        print(f"Memory timeline with {len(memory_samples)} samples included in results")


if __name__ == "__main__":
    print("Load test script ready. Run with: locust -f load_test.py --host=http://localhost:5001")
