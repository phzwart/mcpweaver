#!/usr/bin/env python3
"""
Test script for the refactored MCP server and ReasoningEngine.

This script tests:
1. Server JSON schema generation
2. ReasoningEngine step-based plan format
3. Tool execution flow
"""

import sys
import json
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcpweaver.generic_mcp_server import GenericMCPServer
from mcpweaver.reasoning_engine import ReasoningEngine

def test_server_schema_generation():
    """Test that the server generates proper JSON schemas."""
    print("🧪 Testing server JSON schema generation...")
    
    # Use a simple test config
    test_config = "examples/number_weaver/tools_config.yaml"
    
    try:
        server = GenericMCPServer(test_config)
        tools_list = server.get_tools_list()
        
        print(f"✅ Server loaded {len(tools_list)} tools")
        
        for tool in tools_list:
            print(f"\n📋 Tool: {tool['name']}")
            print(f"   Description: {tool['description']}")
            print(f"   Input Schema: {json.dumps(tool['inputSchema'], indent=2)}")
            print(f"   Output Schema: {json.dumps(tool['outputSchema'], indent=2)}")
            
            # Verify schema structure
            assert 'name' in tool
            assert 'description' in tool
            assert 'inputSchema' in tool
            assert 'outputSchema' in tool
            assert tool['inputSchema']['type'] == 'object'
            assert 'properties' in tool['inputSchema']
            
        print("✅ Server schema generation test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Server schema generation test failed: {e}")
        return False

def test_reasoning_engine_plan_format():
    """Test that the reasoning engine generates step-based plans."""
    print("\n🧪 Testing reasoning engine step-based plan format...")
    
    # Use the reasoning config
    reasoning_config = "configs/reasoning_config.yaml"
    
    try:
        engine = ReasoningEngine(reasoning_config)
        
        # Mock available tools for testing
        mock_tools = [
            {
                "name": "np_mean",
                "description": "Calculate the mean of an array",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "array": {
                            "type": "array",
                            "description": "Input array"
                        }
                    },
                    "required": ["array"]
                },
                "outputSchema": {"type": "object"}
            },
            {
                "name": "np_std",
                "description": "Calculate the standard deviation of an array",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "array": {
                            "type": "array",
                            "description": "Input array"
                        }
                    },
                    "required": ["array"]
                },
                "outputSchema": {"type": "object"}
            }
        ]
        
        # Test schema generation
        schema = engine.generate_json_schema(mock_tools)
        print(f"✅ Generated schema: {json.dumps(schema, indent=2)}")
        
        # Verify schema structure
        assert schema['type'] == 'object'
        assert 'plan' in schema['properties']
        assert schema['properties']['plan']['type'] == 'array'
        assert 'confidence' in schema['properties']
        
        print("✅ Reasoning engine plan format test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Reasoning engine plan format test failed: {e}")
        return False

def test_fuzzy_matching():
    """Test the fuzzy matching functionality."""
    print("\n🧪 Testing fuzzy matching...")
    
    try:
        engine = ReasoningEngine("configs/reasoning_config.yaml")
        
        available_tools = ["np_mean", "np_std", "torch_tensor"]
        
        # Test exact match
        result = engine._find_best_tool_match("np_mean", available_tools)
        assert result == "np_mean"
        
        # Test partial match
        result = engine._find_best_tool_match("mean", available_tools)
        assert result == "np_mean"
        
        # Test no match
        result = engine._find_best_tool_match("unknown_tool", available_tools)
        assert result is None
        
        print("✅ Fuzzy matching test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Fuzzy matching test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing refactored MCP system...")
    print("=" * 50)
    
    tests = [
        test_server_schema_generation,
        test_reasoning_engine_plan_format,
        test_fuzzy_matching
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The refactored system is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 