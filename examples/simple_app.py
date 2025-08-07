#!/usr/bin/env python3
"""
Simple App: Using LLMClient for Reasoning + Your Own Execution

This is a practical example showing how to:
1. Use LLMClient for pure reasoning
2. Handle MCP server communication yourself
3. Execute actions and format responses
"""

import sys
import json
import requests
from pathlib import Path

# Add the src directory to the path so we can import mcpweaver
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcpweaver.llm_client import LLMClient

class SimpleApp:
    """Simple application that uses LLMClient for reasoning only."""
    
    def __init__(self, config_path: str):
        """Initialize the app with reasoning engine and MCP server connection."""
        # Initialize reasoning engine (no execution)
        self.llm_client = LLMClient(config_path)
        
        # Get MCP server configuration from the same config
        mcp_config = self.llm_client.config.get('mcp_server', {})
        self.mcp_server_url = f"http://{mcp_config.get('host', 'localhost')}:{mcp_config.get('port', 8080)}"
        self.timeout = mcp_config.get('timeout', 10)
        
        print(f"🚀 SimpleApp initialized")
        print(f"📋 Config: {config_path}")
        print(f"🔗 MCP Server: {self.mcp_server_url}")
    
    def get_available_tools(self):
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
                tools = result.get("result", [])
                print(f"✅ Found {len(tools)} tools from server")
                return tools
            else:
                print(f"❌ HTTP error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting tools: {e}")
            return []
    
    def execute_tool(self, tool_name: str, arguments: dict):
        """Execute a single tool on the MCP server."""
        try:
            print(f"🔧 Executing: {tool_name}")
            print(f"📝 Arguments: {arguments}")
            
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
                    tool_result = result["result"]
                    print(f"✅ {tool_name} result: {tool_result}")
                    return tool_result
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
    
    def ask(self, query: str):
        """Main function: Ask the app to do something."""
        print(f"\n🤖 Processing: '{query}'")
        print("=" * 50)
        
        # Step 1: Get available tools from server
        print("📋 Getting available tools...")
        available_tools = self.get_available_tools()
        
        if not available_tools:
            return "❌ No tools available from MCP server"
        
        # Step 2: Let LLM reason about the query
        print("🧠 Asking LLM to reason about the query...")
        action_plan = self.llm_client.reason_about_query(query, available_tools)
        
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
        
        # Step 3: Execute the actions
        print("\n🚀 Executing actions...")
        results = {}
        
        for tool_name in selected_tools:
            tool_args = arguments.get(tool_name, {})
            result = self.execute_tool(tool_name, tool_args)
            results[tool_name] = result
        
        # Step 4: Format the response
        return self.format_response(query, action_plan, results)
    
    def format_response(self, query: str, action_plan: dict, results: dict):
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
        response_parts.append(f"Query: '{query}'")
        response_parts.append(f"Tools executed: {len(results)}")
        
        return "\n".join(response_parts)

def main():
    """Main function - demonstrates how to use the SimpleApp."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python simple_app.py <config.yaml> [query]")
        print("Example: python simple_app.py examples/file_system_weaver/client_config.yaml 'List files in docs'")
        print("\nMake sure your MCP server is running first!")
        return
    
    config_path = sys.argv[1]
    query = sys.argv[2] if len(sys.argv) > 2 else "List files in the current directory"
    
    try:
        # Create the app
        app = SimpleApp(config_path)
        
        # Ask it to do something
        response = app.ask(query)
        
        print("\n" + "=" * 60)
        print("🎯 RESPONSE")
        print("=" * 60)
        print(response)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 