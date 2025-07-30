#!/usr/bin/env python3
"""
Test script to verify if the infer parameter is working correctly.
This will test both the API endpoint and examine the memory client behavior.
"""

import requests
import json

def test_infer_parameter():
    base_url = "http://localhost:8765"
    
    print("=== Testing infer parameter functionality ===\n")
    
    # Test 1: infer=true (should use LLM inference)
    print("🔍 Test 1: infer=true (with LLM inference)")
    payload_true = {
        "text": "I am a senior software engineer specializing in machine learning",
        "user_id": "test-user-infer",
        "infer": True
    }
    
    response_true = requests.post(f"{base_url}/api/v1/memories/", 
                                 json=payload_true, 
                                 headers={"Content-Type": "application/json"})
    
    print(f"Status: {response_true.status_code}")
    if response_true.status_code == 200:
        result_true = response_true.json()
        print(f"Result: {json.dumps(result_true, indent=2)}")
    else:
        print(f"Error: {response_true.text}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: infer=false (should NOT use LLM inference)
    print("🔍 Test 2: infer=false (without LLM inference)")
    payload_false = {
        "text": "User is an expert in Python programming. User prefers Django over Flask.",
        "user_id": "test-user-infer", 
        "infer": False
    }
    
    response_false = requests.post(f"{base_url}/api/v1/memories/", 
                                  json=payload_false, 
                                  headers={"Content-Type": "application/json"})
    
    print(f"Status: {response_false.status_code}")
    if response_false.status_code == 200:
        result_false = response_false.json()
        print(f"Result: {json.dumps(result_false, indent=2)}")
    else:
        print(f"Error: {response_false.text}")
    
    print("\n" + "="*50 + "\n")
    
    # Retrieve all memories for this test user to compare
    print("🔍 Retrieving all memories for comparison:")
    filter_payload = {"user_id": "test-user-infer"}
    filter_response = requests.post(f"{base_url}/api/v1/memories/filter", 
                                   json=filter_payload,
                                   headers={"Content-Type": "application/json"})
    
    if filter_response.status_code == 200:
        memories = filter_response.json()
        print("All memories for test user:")
        for memory in memories.get('items', []):
            print(f"- ID: {memory['id']}")
            print(f"  Content: {memory['content']}")
            print(f"  Created: {memory['created_at']}")
            print()
    else:
        print(f"Error retrieving memories: {filter_response.text}")

if __name__ == "__main__":
    test_infer_parameter()
