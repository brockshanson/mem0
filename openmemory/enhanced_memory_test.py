#!/usr/bin/env python3
"""
Enhanced Cross-Memory Relationship Test Suite

This test suite validates the fixes for cross-memory logic issues identified
in the troubleshooting document, including:
1. Inappropriate deletions of unrelated memories
2. Minimal content processing failures
3. Phantom memory operations
4. Cross-category relationship violations
"""

import requests
import json
import time
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8765/api/v1/memories"
MCP_BASE_URL = "http://localhost:8765"  # Adjust if MCP has different endpoint

class MemoryTestSuite:
    """Comprehensive test suite for cross-memory relationship validation"""
    
    def __init__(self):
        self.test_user_id = "enhanced-test-user"
        self.test_results = []
        self.created_memories = []
    
    def cleanup_test_memories(self):
        """Clean up test memories"""
        if self.created_memories:
            try:
                response = requests.delete(f"{API_BASE_URL}/", json={
                    "memory_ids": self.created_memories,
                    "user_id": self.test_user_id
                }, timeout=30)
                logger.info(f"Cleanup: {response.status_code}")
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")
        self.created_memories = []
    
    def create_memory(self, text: str, infer: bool = True, expected_success: bool = True, 
                     test_name: str = "") -> Dict[str, Any]:
        """Create a memory and track the result"""
        logger.info(f"\n=== {test_name} ===")
        logger.info(f"Creating memory: '{text}' (infer={infer})")
        
        payload = {
            "text": text,
            "user_id": self.test_user_id,
            "infer": infer
        }
        
        try:
            response = requests.post(API_BASE_URL, json=payload, timeout=30)
            result = {
                "test_name": test_name,
                "input_text": text,
                "infer": infer,
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.status_code == 200 else response.text,
                "expected_success": expected_success
            }
            
            # Track created memory IDs
            if result["success"] and isinstance(result["response"], dict):
                if "results" in result["response"]:
                    for item in result["response"]["results"]:
                        if "id" in item:
                            self.created_memories.append(item["id"])
                elif "id" in result["response"]:
                    self.created_memories.append(result["response"]["id"])
            
            logger.info(f"Result: {result['success']} - {result['status_code']}")
            if result["success"]:
                logger.info(f"Response: {json.dumps(result['response'], indent=2)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in {test_name}: {e}")
            return {
                "test_name": test_name,
                "input_text": text,
                "infer": infer,
                "success": False,
                "error": str(e),
                "expected_success": expected_success
            }
    
    def list_memories(self) -> List[Dict]:
        """List current memories"""
        try:
            response = requests.get(f"{API_BASE_URL}/", params={
                "user_id": self.test_user_id
            }, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            else:
                logger.error(f"Failed to list memories: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing memories: {e}")
            return []
    
    def test_minimal_content_handling(self):
        """Test Priority 2: Minimal Content Processing Pipeline"""
        logger.info("\n" + "="*50)
        logger.info("TESTING: Minimal Content Handling")
        logger.info("="*50)
        
        # Test cases from troubleshooting document
        minimal_content_tests = [
            ("Blue.", True),
            ("Happy.", True),
            ("I like cats.", True),
            ("Red.", True),
            ("Yes.", True)
        ]
        
        for text, infer in minimal_content_tests:
            result = self.create_memory(
                text, 
                infer=infer, 
                expected_success=True,
                test_name=f"Minimal Content: '{text}'"
            )
            self.test_results.append(result)
            time.sleep(2)  # Brief pause between tests
    
    def test_cross_category_boundaries(self):
        """Test Priority 1: Cross-Memory Relationality Logic"""
        logger.info("\n" + "="*50)
        logger.info("TESTING: Cross-Category Boundary Enforcement")
        logger.info("="*50)
        
        # Create base memories in different semantic categories
        base_memories = [
            ("I work as a software engineer at Google", "work/technology"),
            ("I love listening to jazz music and blues", "entertainment/music"),
            ("I exercise regularly and eat healthy food", "health/wellness"),
            ("I enjoy reading science fiction novels", "personal/hobbies")
        ]
        
        # Create base memories
        for text, category in base_memories:
            result = self.create_memory(
                text,
                infer=True,
                expected_success=True,
                test_name=f"Base Memory ({category}): '{text}'"
            )
            self.test_results.append(result)
            time.sleep(3)  # Allow processing time
        
        # Test cross-category additions that should NOT affect existing memories
        cross_category_tests = [
            ("I enjoy podcasts about technology", "Should NOT delete work memory"),
            ("I listen to classical music concerts", "Should NOT delete jazz memory"),
            ("I drink coffee every morning", "Should NOT delete any memory"),
            ("I use VS Code for programming", "Should reasonably relate to work"),
        ]
        
        for text, expectation in cross_category_tests:
            memories_before = len(self.list_memories())
            logger.info(f"Memories before: {memories_before}")
            
            result = self.create_memory(
                text,
                infer=True,
                expected_success=True,
                test_name=f"Cross-Category Test: '{text}' - {expectation}"
            )
            self.test_results.append(result)
            
            memories_after = len(self.list_memories())
            logger.info(f"Memories after: {memories_after}")
            
            # Log if memories were inappropriately deleted
            if memories_after < memories_before:
                logger.warning(f"POTENTIAL ISSUE: Memory count decreased from {memories_before} to {memories_after}")
            
            time.sleep(3)
    
    def test_appropriate_relationships(self):
        """Test appropriate memory relationships that SHOULD occur"""
        logger.info("\n" + "="*50) 
        logger.info("TESTING: Appropriate Memory Relationships")
        logger.info("="*50)
        
        # Test related content that should reasonably connect
        related_tests = [
            ("I'm learning Python programming", "Base programming memory"),
            ("Python is my favorite programming language", "Should relate to Python learning"),
            ("I use PyCharm IDE for Python development", "Should enhance Python knowledge"),
        ]
        
        for text, expectation in related_tests:
            result = self.create_memory(
                text,
                infer=True,
                expected_success=True,
                test_name=f"Related Content: '{text}' - {expectation}"
            )
            self.test_results.append(result)
            time.sleep(3)
    
    def test_raw_storage_mode(self):
        """Test infer=false mode for structured data"""
        logger.info("\n" + "="*50)
        logger.info("TESTING: Raw Storage Mode (infer=false)")
        logger.info("="*50)
        
        structured_data_tests = [
            "User favorite programming language is Python and uses PyCharm IDE",
            "Preferred coffee shop: Blue Bottle Coffee on Market Street",
            "Meeting scheduled: John Smith, Tuesday 3pm, Project Alpha discussion",
            "Contact: Dr. Sarah Jones, (555) 123-4567, cardiologist"
        ]
        
        for text in structured_data_tests:
            result = self.create_memory(
                text,
                infer=False,
                expected_success=True,
                test_name=f"Raw Storage: '{text}'"
            )
            self.test_results.append(result)
            time.sleep(2)
    
    def run_all_tests(self):
        """Run the complete test suite"""
        logger.info("Starting Enhanced Memory Test Suite")
        logger.info("=" * 60)
        
        try:
            # Clean up any existing test data
            self.cleanup_test_memories()
            
            # Run test suites
            self.test_minimal_content_handling()
            self.test_cross_category_boundaries()
            self.test_appropriate_relationships()
            self.test_raw_storage_mode()
            
            # Generate report
            self.generate_test_report()
            
        finally:
            # Cleanup
            logger.info("\nCleaning up test memories...")
            self.cleanup_test_memories()
    
    def generate_test_report(self):
        """Generate a comprehensive test report"""
        logger.info("\n" + "="*60)
        logger.info("TEST REPORT SUMMARY")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.get("success", False))
        failed_tests = total_tests - successful_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Successful: {successful_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        # List failed tests
        if failed_tests > 0:
            logger.info("\nFAILED TESTS:")
            for result in self.test_results:
                if not result.get("success", False):
                    logger.info(f"- {result['test_name']}: {result.get('error', 'Unknown error')}")
        
        # Save detailed report
        report_data = {
            "test_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": (successful_tests/total_tests)*100
            },
            "detailed_results": self.test_results
        }
        
        with open("enhanced_memory_test_report.json", "w") as f:
            json.dump(report_data, f, indent=2)
        
        logger.info("\nDetailed report saved to: enhanced_memory_test_report.json")


if __name__ == "__main__":
    test_suite = MemoryTestSuite()
    test_suite.run_all_tests()