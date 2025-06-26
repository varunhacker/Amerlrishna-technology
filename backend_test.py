#!/usr/bin/env python3
import requests
import json
import time
import pytest
from datetime import datetime
import os
import sys

# Get the backend URL from the frontend .env file
BACKEND_URL = "https://1f0b9877-d7fc-43e2-a051-04ded491dfce.preview.emergentagent.com"
API_BASE_URL = f"{BACKEND_URL}/api"

# List of valid Indian states for testing
VALID_STATES = [
    "Andhra Pradesh", "Bihar", "Delhi", "Gujarat", "Karnataka", 
    "Kerala", "Maharashtra", "Tamil Nadu", "Uttar Pradesh"
]

# Test categories
VALID_CATEGORIES = [
    "politics", "economy", "education", "science", 
    "environment", "sports", "health", "defense", "general"
]

# Search keywords for testing
SEARCH_KEYWORDS = ["israel", "economy", "education", "climate", "election"]

class TestCurrentAffairsAPI:
    """Test suite for the Current Affairs API"""
    
    def setup_method(self):
        """Setup method that runs before each test"""
        print(f"\nTesting against API at: {API_BASE_URL}")
    
    def test_root_endpoint(self):
        """Test the root API endpoint"""
        response = requests.get(f"{API_BASE_URL}/")
        assert response.status_code == 200
        data = response.json()
        
        # Verify the response structure
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data
        assert isinstance(data["endpoints"], list)
        
        # Check if all required endpoints are listed
        required_endpoints = [
            "/api/news/global", 
            "/api/news/india", 
            "/api/news/state/{state_name}", 
            "/api/news/search"
        ]
        for endpoint in required_endpoints:
            assert endpoint in data["endpoints"]
        
        print(f"✅ Root endpoint test passed")
    
    def test_global_news_endpoint(self):
        """Test the global news endpoint"""
        response = requests.get(f"{API_BASE_URL}/news/global")
        assert response.status_code == 200
        data = response.json()
        
        # Verify the response structure
        assert "news" in data
        assert "total" in data
        assert "source" in data
        assert "status" in data
        assert data["status"] == "success"
        
        # Verify we have news items
        assert isinstance(data["news"], list)
        assert data["total"] > 0
        assert len(data["news"]) == data["total"]
        
        # Verify the structure of a news item
        if data["news"]:
            news_item = data["news"][0]
            required_fields = ["id", "title", "source", "is_global", "category", "published_at", "scraped_at"]
            for field in required_fields:
                assert field in news_item
            
            # Verify global flag is set correctly
            assert news_item["is_global"] == True
        
        print(f"✅ Global news endpoint test passed with {data['total']} articles")
    
    def test_india_news_endpoint(self):
        """Test the India news endpoint"""
        response = requests.get(f"{API_BASE_URL}/news/india")
        assert response.status_code == 200
        data = response.json()
        
        # Verify the response structure
        assert "news" in data
        assert "total" in data
        assert "source" in data
        assert "status" in data
        assert data["status"] == "success"
        
        # Verify the structure of a news item if we have any
        if data["news"]:
            news_item = data["news"][0]
            required_fields = ["id", "title", "source", "is_global", "published_at", "scraped_at"]
            for field in required_fields:
                assert field in news_item
            
            # Verify global flag is set correctly
            assert news_item["is_global"] == False
            
            # Some items should have state/district tags
            has_state_tags = any(item.get("state") for item in data["news"])
            print(f"Indian news with state tags: {has_state_tags}")
        
        print(f"✅ India news endpoint test passed with {data['total']} articles")
    
    def test_state_news_endpoint(self):
        """Test the state-specific news endpoint"""
        # Test with valid states
        for state in VALID_STATES:
            print(f"Testing state: {state}")
            response = requests.get(f"{API_BASE_URL}/news/state/{state}")
            
            # Some states might not have news, so we only check status code
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify the response structure
                assert "news" in data
                assert "total" in data
                assert "state" in data
                assert "districts" in data
                
                # Verify state name matches
                assert data["state"] == state
                
                # Verify districts list
                assert isinstance(data["districts"], list)
                
                # Verify news items if any
                if data["news"]:
                    for news_item in data["news"]:
                        assert news_item["state"] == state
                
                print(f"  ✅ {state} news endpoint test passed with {data['total']} articles")
            else:
                print(f"  ⚠️ No news found for {state}")
        
        # Test with invalid state
        invalid_state = "InvalidState"
        response = requests.get(f"{API_BASE_URL}/news/state/{invalid_state}")
        assert response.status_code == 404
        print(f"✅ Invalid state test passed with status code {response.status_code}")
    
    def test_search_endpoint(self):
        """Test the search endpoint with various queries"""
        # Test with different keywords
        for keyword in SEARCH_KEYWORDS:
            print(f"Testing search with keyword: {keyword}")
            response = requests.get(f"{API_BASE_URL}/news/search?q={keyword}")
            assert response.status_code == 200
            data = response.json()
            
            # Verify the response structure
            assert "news" in data
            assert "total" in data
            assert "query" in data
            assert "filters" in data
            
            # Verify query matches
            assert data["query"] == keyword
            
            print(f"  ✅ Search for '{keyword}' returned {data['total']} results")
        
        # Test with state filter
        if VALID_STATES:
            state = VALID_STATES[0]
            response = requests.get(f"{API_BASE_URL}/news/search?q=news&state={state}")
            assert response.status_code == 200
            data = response.json()
            
            # Verify filter is applied
            assert data["filters"]["state"] == state
            
            # If we have results, verify they match the state
            if data["news"]:
                for news_item in data["news"]:
                    if "state" in news_item and news_item["state"]:
                        assert news_item["state"] == state
            
            print(f"  ✅ Search with state filter '{state}' test passed")
        
        # Test with category filter
        if VALID_CATEGORIES:
            category = VALID_CATEGORIES[0]
            response = requests.get(f"{API_BASE_URL}/news/search?q=news&category={category}")
            assert response.status_code == 200
            data = response.json()
            
            # Verify filter is applied
            assert data["filters"]["category"] == category
            
            print(f"  ✅ Search with category filter '{category}' test passed")
    
    def test_states_endpoint(self):
        """Test the states list endpoint"""
        response = requests.get(f"{API_BASE_URL}/states")
        assert response.status_code == 200
        data = response.json()
        
        # Verify the response structure
        assert "states" in data
        assert isinstance(data["states"], dict)
        
        # Verify we have all states
        for state in VALID_STATES:
            assert state in data["states"]
            assert isinstance(data["states"][state], list)
        
        print(f"✅ States endpoint test passed with {len(data['states'])} states")
    
    def test_refresh_endpoint(self):
        """Test the manual refresh endpoint"""
        response = requests.post(f"{API_BASE_URL}/news/refresh")
        assert response.status_code == 200
        data = response.json()
        
        # Verify the response structure
        assert "message" in data
        assert "global_count" in data
        assert "india_count" in data
        assert "last_updated" in data
        
        # Verify counts are reasonable
        assert data["global_count"] >= 0
        assert data["india_count"] >= 0
        
        print(f"✅ Refresh endpoint test passed. Global: {data['global_count']}, India: {data['india_count']}")
    
    def test_data_structure_and_integrity(self):
        """Test the data structure and integrity of news items"""
        # Get global news
        response = requests.get(f"{API_BASE_URL}/news/global")
        assert response.status_code == 200
        global_data = response.json()
        
        # Get India news
        response = requests.get(f"{API_BASE_URL}/news/india")
        assert response.status_code == 200
        india_data = response.json()
        
        # Get states list for validation
        states_response = requests.get(f"{API_BASE_URL}/states")
        assert states_response.status_code == 200
        all_states = list(states_response.json()["states"].keys())
        
        # Combine news items for testing
        all_news = []
        if "news" in global_data:
            all_news.extend(global_data["news"])
        if "news" in india_data:
            all_news.extend(india_data["news"])
        
        if not all_news:
            print("⚠️ No news items found for data structure testing")
            return
        
        # Test data structure of each news item
        for item in all_news:
            # Required fields
            assert "id" in item
            assert "title" in item
            assert "source" in item
            assert "is_global" in item
            assert "published_at" in item
            assert "scraped_at" in item
            
            # Type checking
            assert isinstance(item["id"], str)
            assert isinstance(item["title"], str)
            assert isinstance(item["source"], str)
            assert isinstance(item["is_global"], bool)
            
            # Check dates are in ISO format
            try:
                datetime.fromisoformat(item["published_at"].replace('Z', '+00:00'))
                datetime.fromisoformat(item["scraped_at"].replace('Z', '+00:00'))
            except ValueError:
                assert False, f"Invalid date format: {item['published_at']} or {item['scraped_at']}"
            
            # Check categorization
            if "category" in item and item["category"]:
                assert item["category"] in VALID_CATEGORIES or item["category"] == "general"
            
            # Check state/district for Indian news
            if not item["is_global"] and "state" in item and item["state"]:
                assert item["state"] in VALID_STATES or item["state"] in all_states
        
        print(f"✅ Data structure and integrity test passed for {len(all_news)} news items")
    
    def test_error_handling(self):
        """Test error handling for invalid requests"""
        # Test invalid endpoint
        response = requests.get(f"{API_BASE_URL}/invalid_endpoint")
        assert response.status_code in [404, 405]
        print(f"✅ Invalid endpoint test passed with status code {response.status_code}")
        
        # Test invalid state
        response = requests.get(f"{API_BASE_URL}/news/state/InvalidState")
        assert response.status_code == 404
        print(f"✅ Invalid state test passed with status code {response.status_code}")
        
        # Test search with empty query
        response = requests.get(f"{API_BASE_URL}/news/search")
        assert response.status_code in [400, 422]  # FastAPI returns 422 for validation errors
        print(f"✅ Empty search query test passed with status code {response.status_code}")


if __name__ == "__main__":
    # Run all tests
    test_instance = TestCurrentAffairsAPI()
    test_instance.setup_method()
    
    # List of all test methods
    test_methods = [
        test_instance.test_root_endpoint,
        test_instance.test_global_news_endpoint,
        test_instance.test_india_news_endpoint,
        test_instance.test_state_news_endpoint,
        test_instance.test_search_endpoint,
        test_instance.test_states_endpoint,
        test_instance.test_refresh_endpoint,
        test_instance.test_data_structure_and_integrity,
        test_instance.test_error_handling
    ]
    
    # Run each test and catch exceptions
    results = {"passed": 0, "failed": 0, "tests": []}
    for test_method in test_methods:
        test_name = test_method.__name__
        print(f"\n{'='*50}\nRunning {test_name}...")
        try:
            test_method()
            results["passed"] += 1
            results["tests"].append({"name": test_name, "status": "passed"})
            print(f"✅ {test_name} PASSED")
        except Exception as e:
            results["failed"] += 1
            results["tests"].append({"name": test_name, "status": "failed", "error": str(e)})
            print(f"❌ {test_name} FAILED: {str(e)}")
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"SUMMARY: {results['passed']} tests passed, {results['failed']} tests failed")
    
    if results["failed"] > 0:
        print("\nFailed tests:")
        for test in results["tests"]:
            if test["status"] == "failed":
                print(f"❌ {test['name']}: {test['error']}")
    
    print(f"{'='*50}")
    
    # Exit with appropriate code
    sys.exit(1 if results["failed"] > 0 else 0)