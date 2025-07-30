#!/usr/bin/env python3
"""
Debug script to test the infer parameter behavior in mem0.
This will help us understand why infer=False still calls the LLM.
"""

import logging
import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.memory import get_memory_client

# Set up logging to see HTTP requests
logging.basicConfig(level=logging.INFO)

def test_infer_parameter():
    """Test if infer=False actually prevents LLM calls."""
    try:
        # Get memory client
        memory_client = get_memory_client()
        
        print("Testing infer=True (should make LLM calls):")
        print("-" * 50)
        
        # Test with infer=True
        response_true = memory_client.add(
            "This is a test memory with infer=True",
            user_id="debug-user",
            infer=True,
            metadata={"test": "infer_true"}
        )
        print(f"Response with infer=True: {response_true}")
        
        print("\nTesting infer=False (should NOT make LLM calls):")
        print("-" * 50)
        
        # Test with infer=False
        response_false = memory_client.add(
            "This is a test memory with infer=False",
            user_id="debug-user", 
            infer=False,
            metadata={"test": "infer_false"}
        )
        print(f"Response with infer=False: {response_false}")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_infer_parameter()
