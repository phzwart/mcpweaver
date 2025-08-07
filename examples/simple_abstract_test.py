#!/usr/bin/env python3
"""
Simple test of abstract reasoning with symbolic references.
"""

import json
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcpweaver.abstract_reasoning_engine import AbstractReasoningEngine


def main():
    """Simple test of abstract reasoning."""
    
    # Initialize the abstract reasoning engine
    config_path = "configs/abstract_reasoning_config.yaml"
    engine = AbstractReasoningEngine(config_path)
    
    # Simple tools
    available_tools = [
        {
            "name": "np_mean",
            "description": "Calculate arithmetic mean of array elements",
            "parameters": {
                "a": {"type": "array", "description": "Input array", "required": True}
            }
        }
    ]
    
    # Test query with symbolic reference
    query = "Compute the mean of <numpy array named A>"
    
    # Create symbolic data mapping
    symbolic_data_structures = {
        "A": {
            "type": "numpy_array",
            "shape": "(100, 3)",
            "dtype": "float64"
        }
    }
    
    symbolic_mapping = engine.create_symbolic_data_mapping(symbolic_data_structures)
    
    print("🧠 Simple Abstract Reasoning Test")
    print("=" * 40)
    print(f"Query: {query}")
    print(f"Symbolic mapping: {symbolic_mapping}")
    
    # Get abstract execution plan
    plan = engine.reason_about_query(query, available_tools, symbolic_mapping)
    
    print("\n📋 Result:")
    print(json.dumps(plan, indent=2))
    
    # Test symbolic reference extraction
    test_args = {
        "np_mean": {
            "a": "<numpy array named A>"
        },
        "np_std": {
            "a": "<numpy array named B>"
        }
    }
    
    symbolic_refs = engine._extract_symbolic_references(test_args)
    print(f"\n🔗 Extracted symbolic references: {symbolic_refs}")


if __name__ == "__main__":
    main() 