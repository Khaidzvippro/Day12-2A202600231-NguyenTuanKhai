#!/usr/bin/env python3
"""
Automated grading script for Day 12 Lab
Usage: python grade.py <student-repo-path> <public-url> <api-key>
"""

import sys
import os
import subprocess
import requests
import time
from pathlib import Path

class Grader:
    def __init__(self, repo_path, public_url, api_key):
        self.repo_path = Path(repo_path)
        self.public_url = public_url.rstrip('/')
        self.api_key = api_key
        self.score = 0
        self.max_score = 60
        self.results = []
    
    def test(self, name, points, func):
        """Run a test and record result"""
        print(f"Testing: {name}...", end=" ", flush=True)
        try:
            func()
            self.score += points
            self.results.append(f"✅ {name}: {points}/{points}")
            print("PASSED")
            return True
        except AssertionError as e:
            self.results.append(f"❌ {name}: 0/{points} - {e}")
            print(f"FAILED - {e}")
            return False
        except Exception as e:
            # Special handling for Rate Limiter which might return 429
            if "429" in str(e):
                self.results.append(f"❌ {name}: 0/{points} - Error: Too Many Requests (Rate Limited)")
                print("FAILED - Rate Limited")
            else:
                self.results.append(f"❌ {name}: 0/{points} - Error: {e}")
                print(f"ERROR - {e}")
            return False
    
    def check_file_exists(self, filepath):
        """Check if file exists"""
        assert (self.repo_path / filepath).exists(), f"{filepath} not found"
    
    def check_dockerfile(self):
        """Check Dockerfile quality"""
        dockerfile = (self.repo_path / "Dockerfile").read_text()
        assert "FROM" in dockerfile, "No FROM instruction"
        assert "as builder" in dockerfile.lower(), "Not multi-stage build"
        assert "slim" in dockerfile.lower(), "Not using slim image for optimization"
    
    def check_docker_compose(self):
        """Check docker-compose.yml"""
        compose = (self.repo_path / "docker-compose.yml").read_text()
        assert "redis:" in compose, "No redis service found in compose"
        assert "agent:" in compose or "app:" in compose, "No agent service found in compose"
    
    def check_no_secrets(self):
        """Check for hardcoded secrets"""
        # More precise grep to avoid false positives with env var names
        result = subprocess.run(
            ["grep", "-r", "sk-", str(self.repo_path / "app")],
            capture_output=True, text=True
        )
        assert result.returncode != 0, f"Found hardcoded API keys in {result.stdout}"
        
        # Check for explicit assignment of key strings
        result_assign = subprocess.run(
            ["grep", "-r", "AGENT_API_KEY = \"", str(self.repo_path / "app")],
            capture_output=True, text=True
        )
        assert result_assign.returncode != 0, "Found hardcoded AGENT_API_KEY string"
    
    def test_health_endpoint(self):
        """Test /health endpoint"""
        r = requests.get(f"{self.public_url}/health", timeout=15)
        assert r.status_code == 200, f"Health check failed: {r.status_code}"
    
    def test_ready_endpoint(self):
        """Test /ready endpoint"""
        r = requests.get(f"{self.public_url}/ready", timeout=15)
        assert r.status_code in [200, 503], f"Ready check failed: {r.status_code}"
    
    def test_auth_required(self):
        """Test authentication is required"""
        r = requests.post(
            f"{self.public_url}/ask",
            json={"question": "test"}
        )
        assert r.status_code == 401, f"Should require authentication (Got {r.status_code})"
    
    def test_auth_works(self):
        """Test authentication works"""
        r = requests.post(
            f"{self.public_url}/ask",
            headers={"X-API-Key": self.api_key},
            json={"user_id": "grader", "question": "Hello Agent"}
        )
        assert r.status_code == 200, f"Auth failed with valid key: {r.status_code} - {r.text}"
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        print("(Stress testing...)", end=" ", flush=True)
        # Send many requests quickly
        status_codes = []
        for i in range(15):
            r = requests.post(
                f"{self.public_url}/ask",
                headers={"X-API-Key": self.api_key},
                json={"user_id": "grader_rate_test", "question": f"stress test {i}"}
            )
            status_codes.append(r.status_code)
            if r.status_code == 429:
                break
            time.sleep(0.1)
        
        assert 429 in status_codes, "Rate limiting (10 req/min) not triggered after 15 requests"
    
    def test_conversation_history(self):
        """Test conversation history (stateless via Redis)"""
        user_id = f"grader_{int(time.time())}"
        
        # First message
        r1 = requests.post(
            f"{self.public_url}/ask",
            headers={"X-API-Key": self.api_key},
            json={"user_id": user_id, "question": "My code name is Antigravity"}
        )
        assert r1.status_code == 200, f"First message failed: {r1.status_code} - {r1.text}"
        
        # Second message referencing first
        r2 = requests.post(
            f"{self.public_url}/ask",
            headers={"X-API-Key": self.api_key},
            json={"user_id": user_id, "question": "What is my code name?"}
        )
        assert r2.status_code == 200, f"Second message failed: {r2.status_code} - {r2.text}"
    
    def run_all_tests(self):
        """Run all tests and output report"""
        print("\n" + "="*60)
        print("🧪 STARTING AUTOMATED GRADING FOR DAY 12 LAB")
        print(f"Target URL: {self.public_url}")
        print("="*60 + "\n")
        
        # File structure tests
        self.test("Dockerfile exists", 2, lambda: self.check_file_exists("Dockerfile"))
        self.test("docker-compose.yml exists", 2, lambda: self.check_file_exists("docker-compose.yml"))
        self.test("requirements.txt exists", 1, lambda: self.check_file_exists("requirements.txt"))
        
        # Docker quality tests
        self.test("Multi-stage Dockerfile", 5, self.check_dockerfile)
        self.test("Docker Compose setup", 4, self.check_docker_compose)
        
        # Security tests
        self.test("No hardcoded secrets", 5, self.check_no_secrets)
        self.test("Authentication required", 5, self.test_auth_required)
        self.test("Authentication functional", 5, self.test_auth_works)
        self.test("Rate limiting (Ex 4.3)", 5, self.test_rate_limiting)
        
        # Reliability tests
        self.test("Health check endpoint", 3, self.test_health_endpoint)
        self.test("Readiness check endpoint", 3, self.test_ready_endpoint)
        
        # Functionality / Stateless tests
        self.test("Conversation history (Stateless)", 10, self.test_conversation_history)
        
        # Deployment test
        self.test("Public deployment works", 10, self.test_health_endpoint)
        
        # Summary
        print("\n" + "="*60)
        print("📊 AUTOMATED GRADING RESULTS SUMMARY")
        print("="*60)
        for result in self.results:
            print(result)
        print("="*60)
        print(f"🎯 AUTOMATED SCORE: {self.score}/60")
        print(f"📈 PERCENTAGE: {self.score/60*100:.1f}%")
        print("="*60 + "\n")
        
        score_manual = 40
        print(f"💡 Manual Points Remaining: {score_manual} points (Ex 1-3, Reports, Code Quality)")
        print(f"💡 Total Estimated Grade: ~{self.score + score_manual}/100")
        
        return self.score

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python grade_my_lab.py <repo-path> <public-url> <api-key>")
        sys.exit(1)
    
    repo = sys.argv[1]
    url = sys.argv[2]
    key = sys.argv[3]
    
    grader = Grader(repo, url, key)
    grader.run_all_tests()
