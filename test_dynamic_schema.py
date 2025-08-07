#!/usr/bin/env python3
"""
Test script for dynamic schema generation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcpweaver.llm_client import LLMClient

def test_dynamic_schema():
    """Test dynamic schema generation."""
    print("🧪 Testing dynamic schema generation...")
    
    # Use the simplified config
    config_path = "examples/number_weaver/client_config_simple.yaml"
    
    try:
        # Create client
        client = LLMClient(config_path)
        print(f"✅ Client created with config: {config_path}")
        
        # Test schema generation
        schema = client.generate_json_schema_from_server()
        
        if schema:
            print("✅ Schema generated successfully!")
            print(f"📋 Schema structure:")
            print(f"  - Tools: {schema['properties']['tools']['items']['enum']}")
            print(f"  - Arguments: {list(schema['properties']['arguments']['properties'].keys())}")
        else:
            print("❌ Failed to generate schema")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_dynamic_schema() 