#!/usr/bin/env python3
"""
Example: Using LLMClient as a Pure Reasoning Engine

This demonstrates the clean separation approach:
1. LLMClient does reasoning only
2. Your application handles execution
3. No serialization complexity
4. Full control over execution flow
"""

import sys
import json
from pathlib import Path

# Add the src directory to the path so we can import mcpweaver
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcpweaver.llm_client import LLMClient
import requests

class MyApplication:
    """Your application that uses LLMClient for reasoning only."""
    
    def __init__(self, config_path: str):
        """Initialize with reasoning engine and MCP server connection."""
        # Initialize reasoning engine (no execution)
        self.llm_client = LLMClient(config_path)
        
        # Get MCP server configuration
        mcp_config = self.llm_client.config.get('mcp_server', {})
        self.mcp_server_url = f"http://{mcp_config.get('host', 'localhost')}:{mcp_config.get('port', 8080)}"
        self.timeout = mcp_config.get('timeout', 10)
    
    def get_available_tools(self) -> list:
        """Get available tools from MCP server."""
        try:
            response = requests.post(
                self.mcp_server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("result", [])
            else:
                print(f"❌ HTTP error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting tools: {e}")
            return []
    
    def execute_tool(self, tool_name: str, arguments: dict) -> any:
        """Execute a single tool on the MCP server."""
        try:
            print(f"🔧 Executing: {tool_name} with args: {arguments}")
            
            response = requests.post(
                self.mcp_server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    return result["result"]
                else:
                    error_msg = result.get('error', 'Unknown error')
                    print(f"❌ Tool call failed: {error_msg}")
                    return f"ERROR: {error_msg}"
            else:
                print(f"❌ HTTP error: {response.status_code}")
                return f"ERROR: HTTP {response.status_code}"
                
        except Exception as e:
            print(f"❌ Error executing tool {tool_name}: {e}")
            return f"ERROR: {e}"
    
    def process_query(self, user_query: str) -> str:
        """Process a user query using reasoning-only approach."""
        print(f"🤖 Processing query: {user_query}")
        
        # Step 1: Get available tools from MCP server
        print("📋 Getting available tools...")
        available_tools = self.get_available_tools()
        
        if not available_tools:
            return "❌ No tools available from MCP server"
        
        print(f"✅ Found {len(available_tools)} tools")
        
        # Step 2: Let LLM reason about the query
        print("🧠 Asking LLM to reason about the query...")
        action_plan = self.llm_client.reason_about_query(user_query, available_tools)
        
        if 'error' in action_plan:
            return f"❌ Reasoning failed: {action_plan['error']}"
        
        selected_tools = action_plan.get('tools', [])
        arguments = action_plan.get('arguments', {})
        reasoning = action_plan.get('reasoning', '')
        
        if not selected_tools:
            return "🤔 LLM didn't select any tools to execute"
        
        print(f"✅ LLM selected tools: {' → '.join(selected_tools)}")
        if reasoning:
            print(f"💭 LLM reasoning: {reasoning}")
        
        # Step 3: Execute the actions yourself
        print("🚀 Executing actions...")
        results = {}
        
        for tool_name in selected_tools:
            tool_args = arguments.get(tool_name, {})
            result = self.execute_tool(tool_name, tool_args)
            results[tool_name] = result
            print(f"✅ {tool_name}: {result}")
        
        # Step 4: Format response
        return self.format_response(user_query, action_plan, results)
    
    def format_response(self, query: str, action_plan: dict, results: dict) -> str:
        """Format the final response."""
        response_parts = []
        
        # Include reasoning if available
        reasoning = action_plan.get('reasoning', '')
        if reasoning:
            response_parts.append("🤔 **LLM Reasoning:**")
            response_parts.append(reasoning)
            response_parts.append("")
        
        # Include tool results
        response_parts.append("🔧 **Tool Results:**")
        for tool_name, result in results.items():
            if isinstance(result, str) and result.startswith("ERROR:"):
                response_parts.append(f"❌ **{tool_name}:** {result}")
            else:
                response_parts.append(f"✅ **{tool_name}:** {result}")
        
        response_parts.append("")
        response_parts.append("📊 **Summary:**")
        response_parts.append(f"Processed query: '{query}'")
        response_parts.append(f"Executed {len(results)} tools")
        
        return "\n".join(response_parts)

def main():
    """Main function demonstrating the reasoning-only approach."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python reasoning_only_example.py <config.yaml> [query]")
        print("Example: python reasoning_only_example.py examples/file_system_weaver/client_config.yaml 'List files in docs'")
        return
    
    config_path = sys.argv[1]
    query = sys.argv[2] if len(sys.argv) > 2 else "List files in the current directory"
    
    try:
        # Create your application
        app = MyApplication(config_path)
        
        # Process the query
        response = app.process_query(query)
        
        print("\n" + "="*60)
        print("🎯 FINAL RESPONSE")
        print("="*60)
        print(response)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 