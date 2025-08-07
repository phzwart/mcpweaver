#!/usr/bin/env python3
"""
Abstract Reasoning Example demonstrating symbolic tool selection and argument extraction.

This example shows how to use the AbstractReasoningEngine to reason about tools
and arguments using symbolic references like <numpy array named A> instead of
concrete data values.
"""

import json
import sys
from pathlib import Path

# Add the src directory to the path so we can import mcpweaver
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcpweaver.abstract_reasoning_engine import AbstractReasoningEngine


def main():
    """Demonstrate abstract reasoning with symbolic references."""
    
    # Initialize the abstract reasoning engine
    config_path = "configs/abstract_reasoning_config.yaml"
    engine = AbstractReasoningEngine(config_path)
    
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
        },
        {
            "name": "np_corrcoef",
            "description": "Calculate correlation coefficient between two arrays",
            "parameters": {
                "x": {"type": "array", "description": "First array", "required": True},
                "y": {"type": "array", "description": "Second array", "required": True}
            }
        }
    ]
    
    # Define symbolic data structures (descriptions of data without concrete values)
    symbolic_data_structures = {
        "A": {
            "type": "numpy_array",
            "shape": "(100, 3)",
            "dtype": "float64",
            "description": "Feature matrix with 100 samples and 3 features"
        },
        "B": {
            "type": "numpy_array", 
            "shape": "(50, 2)",
            "dtype": "int32",
            "description": "Target values with 50 samples and 2 classes"
        },
        "C": {
            "type": "numpy_array",
            "shape": "(100,)",
            "dtype": "float64", 
            "description": "Response variable with 100 samples"
        },
        "df": {
            "type": "pandas_dataframe",
            "shape": "(1000, 5)",
            "description": "Dataframe with 1000 rows and 5 columns"
        },
        "data": {
            "type": "list",
            "length": "200",
            "description": "List of 200 data points"
        }
    }
    
    # Create symbolic mapping
    symbolic_mapping = engine.create_symbolic_data_mapping(symbolic_data_structures)
    
    # Example queries using symbolic references
    test_queries = [
        "Compute the mean of <numpy array named A>",
        "Calculate the standard deviation of <numpy array named B>",
        "Find the median of <numpy array named C>",
        "Compute the correlation between <numpy array named A> and <numpy array named C>",
        "Calculate the mean and standard deviation of <dataframe named df>",
        "Find the sum of <list named data>",
        "Compute the mean, median, and standard deviation of <numpy array named A>"
    ]
    
    print("🧠 Abstract Reasoning Example")
    print("=" * 60)
    print("This example demonstrates reasoning about tools and arguments")
    print("using symbolic references instead of concrete data values.")
    print("=" * 60)
    
    # Show symbolic data context
    print("\n📊 Symbolic Data Context:")
    for name, description in symbolic_mapping.items():
        print(f"  {name}: {description}")
    
    print("\n" + "=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Query {i}: {query}")
        print("-" * 40)
        
        # Get abstract execution plan (pure reasoning, no execution)
        plan = engine.reason_about_query(query, available_tools, symbolic_mapping)
        
        # Display the plan
        print("📋 Abstract Execution Plan:")
        print(json.dumps(plan, indent=2))
        
        # Show what would be executed
        if plan.get('tools'):
            print(f"\n🔧 Tools to execute: {', '.join(plan['tools'])}")
            if plan.get('arguments'):
                print("📝 Symbolic Arguments:")
                for tool, args in plan['arguments'].items():
                    print(f"  {tool}: {args}")
        else:
            print("❌ No tools selected")
        
        if plan.get('reasoning'):
            print(f"\n💭 Reasoning: {plan['reasoning']}")
        
        if plan.get('confidence'):
            print(f"🎯 Confidence: {plan['confidence']}")
        
        if plan.get('symbolic_references'):
            print(f"🔗 Symbolic References Found: {', '.join(plan['symbolic_references'])}")
        
        if plan.get('error'):
            print(f"❌ Error: {plan['error']}")
    
    print("\n" + "=" * 60)
    print("✅ Abstract Reasoning Example Completed!")
    print("\nKey benefits of Abstract Reasoning:")
    print("• No concrete data needed for reasoning")
    print("• Can reason about data structures without values")
    print("• Supports symbolic references like <numpy array named A>")
    print("• Useful for planning and analysis before execution")
    print("• Can work with data descriptions and metadata")


if __name__ == "__main__":
    main() 