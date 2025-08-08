# Reasoning Engine

The `ReasoningEngine` is a pure LLM-based reasoning component that performs tool selection and argument extraction without any execution or external dependencies.

## Overview

The ReasoningEngine is designed to be a standalone, stateless component that can run on any server and be used by any application that needs LLM-based reasoning about which tools to use and what arguments to extract.

### Key Features

- **Pure Reasoning**: Only thinks about what tools to use and what arguments to extract
- **No External Dependencies**: Doesn't connect to MCP servers, APIs, or external services
- **Standalone Operation**: Can run on a different server/process than tool execution
- **Clean Interface**: Simple input/output with no side effects
- **Stateless Design**: Each call is independent with no conversation memory

## Installation

The ReasoningEngine is part of the mcpweaver package:

```bash
pip install mcpweaver
```

## Quick Start

```python
from mcpweaver import ReasoningEngine

# Initialize with configuration
engine = ReasoningEngine("configs/reasoning_config.yaml")

# Define available tools (from your application)
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
    }
]

# Get execution plan (pure reasoning, no execution)
result = engine.reason_about_query(
    query="Calculate the mean and standard deviation of [1,2,3,4,5]",
    available_tools=available_tools
)

print(result)
# Output (plan-only):
# {
#   "plan": [
#     {"tool": "np_mean", "arguments": {"a": [1,2,3,4,5]}, "why": "..."},
#     {"tool": "np_std",  "arguments": {"a": [1,2,3,4,5]}, "why": "..."}
#   ],
#   "confidence": 0.95
# }
```

## Configuration

The ReasoningEngine uses a YAML configuration file focused on reasoning behavior:

```yaml
# reasoning_config.yaml
llm:
  model: "phi3:mini"
  provider: "ollama" 
  api_url: "http://localhost:11434/api/generate"
  timeout: 30
  options:
    temperature: 0.1
    top_p: 0.9

reasoning:
  system_prompt_template: |
    You are an AI assistant that selects appropriate tools for user queries.
    
    Available tools:
    {tools}
    
    Your task is to:
    1. Understand what the user wants to accomplish
    2. Select the appropriate tool(s) to use
    3. Extract any required arguments from the user's query
    4. Provide clear reasoning for your choices
    
    Respond with a JSON object containing a step-based plan and confidence.
  
  user_prompt_template: "User query: {query}"
  json_extraction_regex: r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'

response_format:
  include_confidence: true
  include_reasoning: true
  max_tools_per_query: 5
```

### Configuration Sections

#### `llm`
- **model**: The LLM model to use (e.g., "phi3:mini", "llama3.1")
- **provider**: The LLM provider (e.g., "ollama", "openai")
- **api_url**: The API endpoint for the LLM provider
- **timeout**: Request timeout in seconds
- **options**: Additional options for the LLM (temperature, top_p, etc.)

#### `reasoning`
- **system_prompt_template**: Template for the system prompt with `{tools}` placeholder
- **user_prompt_template**: Template for the user prompt with `{query}` placeholder
- **json_extraction_regex**: Regex pattern for extracting JSON from LLM responses

#### `response_format`
- **include_confidence**: Whether to include confidence scores in responses
- **include_reasoning**: Whether to include reasoning explanations
- **max_tools_per_query**: Maximum number of tools to select per query

## API Reference

### ReasoningEngine

#### `__init__(config_path: str)`

Initialize the reasoning engine with a configuration file.

**Parameters:**
- `config_path`: Path to the YAML configuration file

**Raises:**
- `FileNotFoundError`: If the configuration file doesn't exist

#### `reason_about_query(query: str, available_tools: List[Dict]) -> Dict`

Main reasoning method that returns an execution plan.

**Parameters:**
- `query`: User's natural language query
- `available_tools`: List of available tools with their definitions

**Returns:**
```python
{
  "plan": List[{"tool": str, "arguments": dict, "why": str}],
  "confidence": float,
  "reasoning": Optional[str]
}
```

#### `generate_json_schema(available_tools: List[Dict]) -> Optional[Dict]`

Generate JSON schema for step-based LLM responses.

**Parameters:**
- `available_tools`: List of available tools with their definitions

**Returns:**
- JSON schema for structured LLM responses, or `None` if no tools provided

## Tool Definition Format

Tools should be defined as dictionaries with the following structure:

```python
{
    "name": "tool_name",                    # Required: Unique tool identifier
    "description": "Tool description",      # Required: Human-readable description
    "parameters": {                         # Required: Tool parameters
        "param_name": {
            "type": "string",               # Required: Parameter type
            "description": "Param desc",    # Required: Parameter description
            "required": True,               # Optional: Whether parameter is required
            "default": "default_value"      # Optional: Default value
        }
    }
}
```

### Supported Parameter Types

- `string` / `str` → JSON string
- `integer` / `int` → JSON integer
- `number` / `float` → JSON number
- `boolean` / `bool` → JSON boolean
- `array` / `list` → JSON array
- `object` / `dict` → JSON object
- `Any` → JSON string (default)

## Error Handling

The ReasoningEngine handles various error conditions gracefully:

- **LLM API Errors**: Returns error information in the response
- **JSON Parsing Errors**: Uses regex fallback for malformed responses
- **Configuration Errors**: Raises appropriate exceptions during initialization
- **Network Errors**: Returns error information in the response

## Examples

### Basic Usage

```python
from mcpweaver import ReasoningEngine

engine = ReasoningEngine("configs/reasoning_config.yaml")

tools = [
    {
        "name": "calculator",
        "description": "Perform mathematical calculations",
        "parameters": {
            "expression": {"type": "string", "description": "Math expression", "required": True}
        }
    }
]

result = engine.reason_about_query("What is 2+2?", tools)
print(result["plan"][0]["tool"])       # "calculator"
print(result["plan"][0]["arguments"])  # {"expression": "2+2"} (example)
```

### Advanced Usage with Multiple Tools

```python
tools = [
    {
        "name": "file_reader",
        "description": "Read file contents",
        "parameters": {
            "path": {"type": "string", "description": "File path", "required": True}
        }
    },
    {
        "name": "text_analyzer",
        "description": "Analyze text content",
        "parameters": {
            "text": {"type": "string", "description": "Text to analyze", "required": True},
            "analysis_type": {"type": "string", "description": "Type of analysis", "required": False, "default": "sentiment"}
        }
    }
]

plan = engine.reason_about_query(
    "Read the file 'data.txt' and analyze its sentiment",
    tools
)
```

## Testing

Run the unit tests:

```bash
pytest tests/test_reasoning_engine.py
```

Run the example:

```bash
python examples/reasoning_engine_example.py
```

## Benefits

### For Application Developers

1. **Separation of Concerns**: Reasoning and execution are separate
2. **Flexibility**: Can use any tool execution framework
3. **Scalability**: Reasoning can run on different servers
4. **Reliability**: No external dependencies except LLM API
5. **Testability**: Easy to unit test with mocked LLM responses

### For System Architects

1. **Microservices**: Reasoning engine can be a separate service
2. **Load Balancing**: Multiple reasoning engines can handle requests
3. **Caching**: Can cache reasoning results independently
4. **Monitoring**: Can monitor reasoning performance separately
5. **Deployment**: Can deploy reasoning and execution independently

## Notes on Legacy Client

The earlier `LLMClient` has been deprecated in favor of using `ReasoningEngine` with a separate MCP server. If you encounter older examples referencing `LLMClient`, replace them with `ReasoningEngine` as shown above.

## Contributing

The ReasoningEngine is designed to be extensible. Key areas for contribution:

1. **Additional LLM Providers**: Support for more LLM APIs
2. **Enhanced Schema Generation**: More sophisticated JSON schema generation
3. **Better Error Handling**: More specific error types and recovery
4. **Performance Optimization**: Caching, batching, etc.
5. **Additional Configuration Options**: More customization options

## License

The ReasoningEngine is part of the mcpweaver project and follows the same license terms. 