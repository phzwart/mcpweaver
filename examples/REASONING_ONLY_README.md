# Reasoning-Only LLMClient Approach

This demonstrates the **clean separation** approach where the LLMClient is used purely for reasoning, and your application handles execution.

## 🎯 **Why This Approach?**

### **Problems with the Original Approach:**
- Complex serialization logic (`ConversionManager`)
- State management between tool calls
- Hard to test reasoning vs execution separately
- Mixed responsibilities in one class

### **Benefits of Reasoning-Only:**
- ✅ **Clean separation** of concerns
- ✅ **No serialization complexity**
- ✅ **Full control** over execution
- ✅ **Easy to test** reasoning separately
- ✅ **Standard agent pattern**

## 🏗️ **Architecture**

```
User Query → Your App → LLMClient (Reasoning) → Action Plan → Your App (Execution) → Response
```

### **Step-by-Step Flow:**

1. **Your Application** reads user query
2. **Your Application** gets available tools from MCP server
3. **LLMClient** reasons about query given available tools
4. **LLMClient** returns action plan (JSON)
5. **Your Application** executes the actions
6. **Your Application** formats response

## 📝 **Usage Example**

```python
from mcpweaver.llm_client import LLMClient
import requests

class MyApplication:
    def __init__(self, config_path: str):
        # Initialize reasoning engine (no execution)
        self.llm_client = LLMClient(config_path)
        
        # Your MCP server connection
        self.mcp_server_url = "http://localhost:8080"
    
    def process_query(self, user_query: str):
        # Step 1: Get available tools
        available_tools = self.get_available_tools()
        
        # Step 2: Let LLM reason (pure reasoning)
        action_plan = self.llm_client.reason_about_query(user_query, available_tools)
        
        # Step 3: Execute actions yourself
        results = {}
        for tool_name in action_plan['tools']:
            tool_args = action_plan['arguments'].get(tool_name, {})
            result = self.execute_tool(tool_name, tool_args)
            results[tool_name] = result
        
        # Step 4: Format response
        return self.format_response(results)
```

## 🔧 **Key Methods**

### **LLMClient.reason_about_query()**
```python
def reason_about_query(self, query: str, available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure reasoning - returns action plan, doesn't execute anything!"""
```

**Returns:**
```json
{
    "tools": ["list_files", "read_file"],
    "arguments": {
        "list_files": {"directory": "docs"},
        "read_file": {"file_path": "README.md"}
    },
    "reasoning": "User wants to see files in docs directory and read README"
}
```

## 🚀 **Running the Example**

```bash
# Start your MCP server first
python -m mcpweaver.generic_mcp_server examples/file_system_weaver/tools_config.yaml

# In another terminal, run the reasoning-only example
python examples/reasoning_only_example.py examples/file_system_weaver/client_config.yaml "List files in docs"
```

## 🎛️ **Configuration**

The LLMClient still uses the same YAML configuration, but now focuses only on the reasoning parts:

```yaml
llm:
  model: "phi3:mini"
  provider: "ollama"
  api_url: "http://localhost:11434/api/generate"

llm_reasoning:
  system_prompt_template: |
    You are an AI assistant that helps users with operations.
    
    Available tools:
    {tools}
    
    Your task is to select appropriate tools and extract arguments.
    
    Respond with a JSON object containing:
    - "tools": Array of tool names to use
    - "arguments": Object with arguments for each tool
    - "reasoning": Explanation of your reasoning

  user_prompt_template: "User query: {query}"
```

## 🔄 **Migration from Original Approach**

If you're using the original `process_query()` method, you can migrate like this:

```python
# Old way (execution included)
client = LLMClient("config.yaml")
response = client.process_query("List files")

# New way (reasoning only)
client = LLMClient("config.yaml")
action_plan = client.reason_about_query("List files", available_tools)
# Then execute actions yourself
```

## ✅ **Benefits You Get**

1. **No Serialization Complexity**: No `ConversionManager` needed
2. **Simple Data Flow**: JSON in, JSON out
3. **Full Control**: You decide how to handle tool results
4. **Testable**: Test reasoning and execution separately
5. **Extensible**: Easy to add custom execution logic
6. **Standard Pattern**: Follows classic agent architecture

## 🧪 **Testing**

```python
# Test reasoning separately
def test_reasoning():
    client = LLMClient("config.yaml")
    tools = [{"name": "list_files", "description": "List files"}]
    action_plan = client.reason_about_query("List files", tools)
    assert "list_files" in action_plan["tools"]

# Test execution separately  
def test_execution():
    app = MyApplication("config.yaml")
    result = app.execute_tool("list_files", {"directory": "docs"})
    assert result is not None
```

This approach gives you the **best of both worlds** - you can use the existing infrastructure but with your preferred clean architecture! 