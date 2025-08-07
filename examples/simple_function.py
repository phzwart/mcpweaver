#!/usr/bin/env python3
"""
Simple Function: Minimal example of using LLMClient for reasoning

This shows the absolute minimum code needed to:
1. Use LLMClient for reasoning
2. Execute actions yourself
"""

import sys
import requests
from pathlib import Path

# Add the src directory to the path so we can import mcpweaver
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcpweaver.llm_client import LLMClient

def ask_my_app(config_path: str, query: str):
    """
    Simple function that uses LLMClient for reasoning and executes actions.
    
    Args:
        config_path: Path to your YAML config file
        query: What you want the app to do
        
    Returns:
        Formatted response with results
    """
    # Initialize reasoning engine
    llm_client = LLMClient(config_path)
    
    # Get MCP server config
    mcp_config = llm_client.config.get('mcp_server', {})
    mcp_url = f"http://{mcp_config.get('host', 'localhost')}:{mcp_config.get('port', 8080)}"
    timeout = mcp_config.get('timeout', 10)
    
    print(f"🤖 Processing: '{query}'")
    
    # Step 1: Get available tools
    response = requests.post(
        mcp_url,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        },
        timeout=timeout
    )
    
    if response.status_code != 200:
        return f"❌ Could not get tools from server: HTTP {response.status_code}"
    
    available_tools = response.json().get("result", [])
    print(f"✅ Found {len(available_tools)} tools")
    
    # Step 2: Let LLM reason
    action_plan = llm_client.reason_about_query(query, available_tools)
    
    if 'error' in action_plan:
        return f"❌ Reasoning failed: {action_plan['error']}"
    
    selected_tools = action_plan.get('tools', [])
    arguments = action_plan.get('arguments', {})
    
    if not selected_tools:
        return "🤔 LLM didn't select any tools to execute"
    
    print(f"✅ LLM selected: {selected_tools}")
    
    # Step 3: Execute actions
    results = {}
    for tool_name in selected_tools:
        tool_args = arguments.get(tool_name, {})
        
        print(f"🔧 Executing: {tool_name}")
        
        # Call the tool
        tool_response = requests.post(
            mcp_url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": tool_args
                }
            },
            timeout=timeout
        )
        
        if tool_response.status_code == 200:
            tool_result = tool_response.json()
            if "result" in tool_result:
                results[tool_name] = tool_result["result"]
                print(f"✅ {tool_name}: {tool_result['result']}")
            else:
                results[tool_name] = f"ERROR: {tool_result.get('error', 'Unknown error')}"
        else:
            results[tool_name] = f"ERROR: HTTP {tool_response.status_code}"
    
    # Step 4: Format response
    response_parts = []
    response_parts.append("🔧 **Results:**")
    
    for tool_name, result in results.items():
        if isinstance(result, str) and result.startswith("ERROR:"):
            response_parts.append(f"❌ {tool_name}: {result}")
        else:
            response_parts.append(f"✅ {tool_name}: {result}")
    
    response_parts.append("")
    response_parts.append(f"📊 Query: '{query}'")
    response_parts.append(f"📊 Tools executed: {len(results)}")
    
    return "\n".join(response_parts)

def main():
    """Example usage of the simple function."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python simple_function.py <config.yaml> [query]")
        print("Example: python simple_function.py examples/file_system_weaver/client_config.yaml 'List files'")
        return
    
    config_path = sys.argv[1]
    query = sys.argv[2] if len(sys.argv) > 2 else "List files in current directory"
    
    try:
        result = ask_my_app(config_path, query)
        print("\n" + "=" * 50)
        print("🎯 RESULT")
        print("=" * 50)
        print(result)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 