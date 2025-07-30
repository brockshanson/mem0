#!/usr/bin/env python3
"""
MCP Server Test Script
Tests the OpenMemory MCP server functionality to identify timeout issues.
"""

import requests
import json
import time
import sys

def test_mcp_endpoint(base_url="http://localhost:8765"):
    """Test various MCP endpoints for responsiveness and timeout issues."""
    
    print("🧪 Testing OpenMemory MCP Server...")
    print(f"Base URL: {base_url}")
    print("-" * 50)
    
    # Test 1: MCP Message Endpoint
    print("1. Testing MCP Message Endpoint...")
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/mcp/messages/",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            timeout=10
        )
        elapsed = time.time() - start_time
        print(f"   ✅ Response: {response.status_code} (took {elapsed:.2f}s)")
        if response.status_code == 200:
            print(f"   📦 Content: {response.text[:100]}...")
    except requests.exceptions.Timeout:
        print("   ❌ TIMEOUT after 10 seconds")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False
    
    # Test 2: SSE Endpoint (non-blocking test)
    print("\n2. Testing SSE Endpoint (quick connect test)...")
    try:
        start_time = time.time()
        response = requests.get(
            f"{base_url}/mcp/claude/sse/local-user",
            timeout=2,  # Short timeout for SSE test
            stream=True
        )
        elapsed = time.time() - start_time
        print(f"   ✅ SSE Connected: {response.status_code} (took {elapsed:.2f}s)")
        response.close()
    except requests.exceptions.Timeout:
        print("   ⚠️  SSE Timeout (expected for streaming endpoint)")
    except Exception as e:
        print(f"   ❌ SSE ERROR: {e}")
    
    # Test 3: Memory Creation via API
    print("\n3. Testing Memory Creation...")
    try:
        start_time = time.time()
        memory_data = {
            "text": "Test memory for timeout debugging",
            "user_id": "local-user",
            "infer": False
        }
        response = requests.post(
            f"{base_url}/api/v1/memories/",
            json=memory_data,
            timeout=30  # Longer timeout for memory creation
        )
        elapsed = time.time() - start_time
        print(f"   ✅ Memory Created: {response.status_code} (took {elapsed:.2f}s)")
        if response.status_code == 200:
            data = response.json()
            memory_id = data.get('id')
            print(f"   📝 Memory ID: {memory_id}")
            return memory_id
    except requests.exceptions.Timeout:
        print("   ❌ MEMORY CREATION TIMEOUT after 30 seconds")
        return False
    except Exception as e:
        print(f"   ❌ MEMORY CREATION ERROR: {e}")
        return False

def test_memory_search(base_url="http://localhost:8765"):
    """Test memory search functionality."""
    print("\n4. Testing Memory Search...")
    try:
        start_time = time.time()
        response = requests.get(
            f"{base_url}/api/v1/memories/?user_id=local-user&limit=5",
            timeout=15
        )
        elapsed = time.time() - start_time
        print(f"   ✅ Search Response: {response.status_code} (took {elapsed:.2f}s)")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('results', []))
            print(f"   📊 Found {count} memories")
    except requests.exceptions.Timeout:
        print("   ❌ SEARCH TIMEOUT after 15 seconds")
        return False
    except Exception as e:
        print(f"   ❌ SEARCH ERROR: {e}")
        return False

def check_dependencies(base_url="http://localhost:8765"):
    """Check if external dependencies are responding."""
    print("\n5. Checking Dependencies...")
    
    # Check Qdrant
    try:
        start_time = time.time()
        response = requests.get("http://localhost:6333/collections", timeout=5)
        elapsed = time.time() - start_time
        print(f"   ✅ Qdrant: {response.status_code} (took {elapsed:.2f}s)")
    except Exception as e:
        print(f"   ❌ Qdrant Error: {e}")
    
    # Check if Ollama is reachable (if configured)
    try:
        # This might be configured differently, so we'll skip detailed check
        print("   ℹ️  Ollama: Check your local Ollama configuration")
    except Exception as e:
        print(f"   ⚠️  Ollama: {e}")

def main():
    """Run all tests."""
    print("🔍 OpenMemory MCP Server Timeout Diagnostic")
    print("=" * 50)
    
    base_url = "http://localhost:8765"
    
    # Run tests
    memory_id = test_mcp_endpoint(base_url)
    test_memory_search(base_url)
    check_dependencies(base_url)
    
    print("\n" + "=" * 50)
    print("🎯 Timeout Troubleshooting Tips:")
    print("1. If MCP endpoint times out: Check server logs for errors")
    print("2. If Memory Creation times out: Check Ollama/LLM connectivity")
    print("3. If SSE times out in Claude: Check network/firewall settings")
    print("4. If Search times out: Check Qdrant vector store status")
    print("\n💡 Next Steps:")
    print("- Check docker-compose logs for error details")
    print("- Verify Claude Desktop MCP configuration")
    print("- Test with simpler operations first (infer=false)")

if __name__ == "__main__":
    main()
