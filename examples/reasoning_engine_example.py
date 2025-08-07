#!/usr/bin/env python3
"""
Simple example demonstrating the ReasoningEngine.

This example shows how to use the pure reasoning engine to:
1. Initialize with configuration
2. Provide available tools
3. Get execution plans without execution
"""

import json
import sys
from pathlib import Path

# Add the src directory to the path so we can import mcpweaver
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcpweaver import ReasoningEngine


def main():
    """Demonstrate the reasoning engine."""
    
    # Initialize the reasoning engine
    config_path = "configs/reasoning_config.yaml"
    engine = ReasoningEngine(config_path)
    
    # Define available tools (this would come from your application)
    available_tools = [
        {
            "name": "np_mean",
            "description": "Calculate arithmetic mean of array elements",
            "parameters": {
                "a": {"type": "array", "description": "Input array", "required": True}
            }
        },
        {
            "name": "np_std",
            "description": "Calculate standard deviation of array elements",
            "parameters": {
                "a": {"type": "array", "description": "Input array", "required": True}
            }
        },
        {
            "name": "np_median",
            "description": "Calculate median of array elements",
            "parameters": {
                "a": {"type": "array", "description": "Input array", "required": True}
            }
        },
        {
            "name": "np_sum",
            "description": "Calculate sum of array elements",
            "parameters": {
                "a": {"type": "array", "description": "Input array", "required": True}
            }
        }
    ]
    
    # Example queries to test
    test_queries = [
        "Calculate the mean and standard deviation of [1,2,3,4,5]",
        "What is the median of [10, 20, 30, 40, 50]?",
        "Find the sum of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]",
        "Give me the mean, median, and standard deviation of [100, 200, 300, 400, 500]"
    ]
    
    print("🧠 Reasoning Engine Example")
    print("=" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Query {i}: {query}")
        print("-" * 30)
        
        # Get execution plan (pure reasoning, no execution)
        plan = engine.reason_about_query(query, available_tools)
        
        # Display the plan
        print("📋 Execution Plan:")
        print(json.dumps(plan, indent=2))
        
        # Show what would be executed
        if plan.get('tools'):
            print(f"\n🔧 Tools to execute: {', '.join(plan['tools'])}")
            if plan.get('arguments'):
                print("📝 Arguments:")
                for tool, args in plan['arguments'].items():
                    print(f"  {tool}: {args}")
        else:
            print("❌ No tools selected")
        
        if plan.get('reasoning'):
            print(f"\n💭 Reasoning: {plan['reasoning']}")
        
        if plan.get('confidence'):
            print(f"🎯 Confidence: {plan['confidence']}")
        
        if plan.get('error'):
            print(f"❌ Error: {plan['error']}")
    
    print("\n" + "=" * 50)
    print("✅ Example completed!")
    print("\nKey benefits of the ReasoningEngine:")
    print("• Pure reasoning with no side effects")
    print("• No external dependencies except LLM API")
    print("• Can run on different server than execution")
    print("• Clean, simple interface")
    print("• Stateless design")


if __name__ == "__main__":
    main() 