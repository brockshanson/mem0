#!/usr/bin/env python3
"""
Test script to verify infer=true vs infer=false behavior
"""
import requests
import json
import time

API_URL = "http://localhost:8765/api/v1/memories/"

def test_memory_creation(text, infer_value, test_name):
    """Test memory creation with specific infer value"""
    print(f"\n=== {test_name} ===")
    print(f"Input text: '{text}'")
    print(f"infer={infer_value}")
    
    payload = {
        "text": text,
        "user_id": f"test-infer-{infer_value}",
        "infer": infer_value
    }
    
    try:
        response = requests.post(API_URL, 
                               json=payload, 
                               headers={"Content-Type": "application/json"},
                               timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Response:")
            print(json.dumps(result, indent=2))
            
            # Extract and show the memory content
            if 'results' in result:
                for item in result['results']:
                    if 'memory' in item:
                        print(f"📝 Stored memory: '{item['memory']}'")
                        print(f"🔍 Event: {item.get('event', 'unknown')}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏱️ Request timed out - this might indicate the LLM is processing")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    # Test with simple, clean text
    test_text = "User enjoys hiking and mountain biking on weekends"
    
    # Test infer=false (should store raw text)
    test_memory_creation(test_text, False, "TEST 1: infer=false")
    
    # Wait a moment between tests
    time.sleep(2)
    
    # Test infer=true (should process with LLM)
    test_memory_creation(test_text, True, "TEST 2: infer=true")

if __name__ == "__main__":
    main()
