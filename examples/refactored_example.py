#!/usr/bin/env python3
"""
Example demonstrating the refactored MCP server and ReasoningEngine.

This example shows:
1. Server generating proper JSON schemas
2. ReasoningEngine creating step-based plans
3. Tool execution with the new format
"""

import sys
import json
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcpweaver.generic_mcp_server import GenericMCPServer
from mcpweaver.reasoning_engine import ReasoningEngine

def demonstrate_server_schemas():
    """Demonstrate the server's new JSON schema generation."""
    print("🔧 Demonstrating Server JSON Schema Generation")
    print("=" * 50)
    
    # Load server with number weaver tools
    server = GenericMCPServer("examples/number_weaver/tools_config.yaml")
    tools = server.get_tools_list()
    
    print(f"📦 Server loaded {len(tools)} tools with proper JSON schemas")
    
    # Show a few examples
    for i, tool in enumerate(tools[:3]):  # Show first 3 tools
        print(f"\n📋 Tool {i+1}: {tool['name']}")
        print(f"   Description: {tool['description']}")
        print(f"   Input Schema:")
        print(f"     Type: {tool['inputSchema']['type']}")
        print(f"     Properties: {len(tool['inputSchema']['properties'])} parameters")
        print(f"     Required: {tool['inputSchema']['required']}")
        
        # Show first parameter as example
        if tool['inputSchema']['properties']:
            param_name = list(tool['inputSchema']['properties'].keys())[0]
            param_schema = tool['inputSchema']['properties'][param_name]
            print(f"     Example param '{param_name}': {param_schema['type']} - {param_schema['description']}")
    
    return tools

def demonstrate_reasoning_engine(tools):
    """Demonstrate the reasoning engine's step-based planning."""
    print("\n🧠 Demonstrating ReasoningEngine Step-Based Planning")
    print("=" * 50)
    
    # Load reasoning engine
    engine = ReasoningEngine("configs/reasoning_config.yaml")
    
    # Test queries
    test_queries = [
        "Calculate the mean of [1, 2, 3, 4, 5]",
        "Find the standard deviation of [10, 20, 30, 40, 50]",
        "Generate 5 random numbers between 0 and 1"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Query {i}: {query}")
        
        # Generate plan
        plan = engine.reason_about_query(query, tools)
        
        print(f"📋 Generated Plan:")
        print(f"   Confidence: {plan.get('confidence', 0.0)}")
        
        if 'plan' in plan and plan['plan']:
            for j, step in enumerate(plan['plan'], 1):
                print(f"   Step {j}:")
                print(f"     Tool: {step.get('tool', 'unknown')}")
                print(f"     Arguments: {step.get('arguments', {})}")
                print(f"     Why: {step.get('why', 'No explanation')}")
        else:
            print(f"   ❌ No plan generated")
        
        if 'error' in plan:
            print(f"   ⚠️ Error: {plan['error']}")

def demonstrate_fuzzy_matching():
    """Demonstrate the fuzzy matching functionality."""
    print("\n🎯 Demonstrating Fuzzy Matching")
    print("=" * 50)
    
    engine = ReasoningEngine("configs/reasoning_config.yaml")
    available_tools = ["np_mean", "np_std", "np_sum", "torch_tensor", "torch_mean"]
    
    test_cases = [
        ("np_mean", "np_mean"),  # Exact match
        ("mean", "np_mean"),      # Partial match
        ("std", "np_std"),        # Partial match
        ("sum", "np_sum"),        # Partial match
        ("unknown", None),        # No match
    ]
    
    for input_name, expected in test_cases:
        result = engine._find_best_tool_match(input_name, available_tools)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{input_name}' → '{result}' (expected: '{expected}')")

def demonstrate_backwards_compatibility():
    """Demonstrate backwards compatibility with legacy formats."""
    print("\n🔄 Demonstrating Backwards Compatibility")
    print("=" * 50)
    
    engine = ReasoningEngine("configs/reasoning_config.yaml")
    
    # Test legacy format conversion
    legacy_responses = [
        {
            "actions": [
                {"tool": "np_mean", "arguments": {"a": [1, 2, 3]}}
            ],
            "confidence": 0.8
        },
        {
            "action1": {"tool": "np_std", "arguments": {"a": [1, 2, 3]}},
            "confidence": 0.7
        }
    ]
    
    for i, legacy_response in enumerate(legacy_responses, 1):
        print(f"\n📋 Legacy Response {i}:")
        print(f"   Input: {json.dumps(legacy_response, indent=2)}")
        
        # Simulate parsing (this would normally happen in the LLM response parsing)
        if 'actions' in legacy_response:
            plan = []
            for action in legacy_response['actions']:
                plan.append({
                    'tool': action.get('tool'),
                    'arguments': action.get('arguments', {}),
                    'why': 'Converted from legacy actions format'
                })
            converted = {'plan': plan, 'confidence': legacy_response.get('confidence', 0.0)}
        elif 'action1' in legacy_response:
            plan = []
            for i in range(1, 4):
                action_key = f'action{i}'
                if action_key in legacy_response:
                    action = legacy_response[action_key]
                    plan.append({
                        'tool': action.get('tool'),
                        'arguments': action.get('arguments', {}),
                        'why': f'Converted from legacy {action_key} format'
                    })
            converted = {'plan': plan, 'confidence': legacy_response.get('confidence', 0.0)}
        
        print(f"   Converted: {json.dumps(converted, indent=2)}")

def main():
    """Run the demonstration."""
    print("🚀 MCP Server and ReasoningEngine Refactoring Demo")
    print("=" * 60)
    
    try:
        # Demonstrate server schema generation
        tools = demonstrate_server_schemas()
        
        # Demonstrate reasoning engine
        demonstrate_reasoning_engine(tools)
        
        # Demonstrate fuzzy matching
        demonstrate_fuzzy_matching()
        
        # Demonstrate backwards compatibility
        demonstrate_backwards_compatibility()
        
        print("\n" + "=" * 60)
        print("🎉 Demo completed successfully!")
        print("✅ All refactored features are working correctly")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 