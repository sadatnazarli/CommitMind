import os
import requests
import json
from typing import Dict, Optional
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta
import hashlib

load_dotenv()

class AIExplainer:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set")

        self.cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)

        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "CommitMind"
        }
        self.last_request_time = 0
        self.min_request_interval = 1  # Minimum time between requests in seconds

    def _get_cache_key(self, commit_data: Dict) -> str:
        """Generate a unique cache key for a commit"""
        content = f"{commit_data['hash']}{commit_data['message']}{commit_data['diff']}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if it exists and is not expired"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    # Check if cache is still valid (24 hours)
                    if datetime.fromisoformat(cached_data['timestamp']) > datetime.now() - timedelta(hours=24):
                        return cached_data['explanation']
            except (json.JSONDecodeError, KeyError, ValueError):
                # If cache file is corrupted, ignore it
                pass
        return None

    def _cache_response(self, cache_key: str, explanation: str):
        """Cache the response"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'explanation': explanation
        }
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            print(f"Warning: Failed to cache response: {str(e)}")

    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def explain_commit(self, commit_data: Dict) -> str:
        """Generate an explanation for a commit using OpenRouter API with caching and improved error handling"""
        # Check cache first
        cache_key = self._get_cache_key(commit_data)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            print(f"Using cached response for commit {commit_data['hash'][:7]}")
            return cached_response

        # Limit the diff size to avoid token limits
        diff = commit_data['diff']
        if len(diff) > 500:
            diff = diff[:500] + "\n... (diff truncated for length)"

        content = f"""Briefly explain this Git commit (2-3 sentences max):
Commit: {commit_data['message']}
Changes: {diff}"""

        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that explains Git commits in simple terms."
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": 0.3,
            "max_tokens": 150
        }

        max_retries = 3
        base_delay = 2
        for attempt in range(max_retries):
            try:
                self._rate_limit()  # Apply rate limiting
                print(f"Making API request for commit {commit_data['hash'][:7]} (attempt {attempt + 1}/{max_retries})")

                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=15
                )

                if response.status_code == 429:  # Rate limit exceeded
                    retry_after = int(response.headers.get('Retry-After', base_delay * (attempt + 1)))
                    print(f"Rate limit exceeded. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                explanation = response.json()['choices'][0]['message']['content']

                # Cache successful response
                self._cache_response(cache_key, explanation)
                print(f"Got response for commit {commit_data['hash'][:7]}")
                return explanation

            except requests.exceptions.Timeout:
                print(f"Request timed out for commit {commit_data['hash'][:7]}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                return "Error: Request timed out. Please try again later."

            except requests.exceptions.RequestException as e:
                print(f"API request failed for commit {commit_data['hash'][:7]}: {str(e)}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                return f"Error: Could not generate explanation. {str(e)}"

            except Exception as e:
                print(f"Unexpected error for commit {commit_data['hash'][:7]}: {str(e)}")
                return "Error: An unexpected error occurred. Please try again later."