# MCP Weaver Examples

This directory contains various examples demonstrating how to use MCP Weaver with different types of tools and configurations.

## Available Examples

### 📁 File System Surfer
**Location**: `file_system_weaver/`

A complete example showing how to build file system tools for browsing, reading, and analyzing files.

**Features**:
- List files in directories
- Read file contents with line limits
- Count lines and analyze file structure
- Get detailed file metadata
- Search files by pattern or content

**Usage**:
```bash
# Start server (from project root)
mcpweaver server examples/file_system_weaver/tools_config.yaml --host localhost --port 8080

# Run client (from project root)
mcpweaver client examples/file_system_weaver/client_config.yaml "List files"
```

## Example Structure

Each example follows this structure:
```
example_name/
├── README.md           # Example documentation
├── tools_config.yaml   # Server configuration
├── client_config.yaml  # Client configuration
└── tools/             # Tool implementations
    ├── __init__.py
    ├── tool1.py
    └── tool2.py
```

## Creating New Examples

1. Create a new subdirectory for your example
2. Add your tool implementations in a `tools/` subdirectory
3. Create `tools_config.yaml` with your tool definitions
4. Create `client_config.yaml` with your client behavior
5. Add a `README.md` explaining your example

## Configuration Patterns

### Server Configuration (`tools_config.yaml`)
```yaml
tools:
  my_tool:
    python_path: "my_tool.my_function"
    full_path: "examples/my_example/tools"  # Directory to add to Python path
    workflow_context:
      description: "Tool description"
```

### Client Configuration (`client_config.yaml`)
```yaml
llm:
  model: "phi3:mini"
  provider: "ollama"

mcp_server:
  host: "localhost"
  port: 8080
  timeout: 10

# Tool definitions, prompts, behavior, etc.
```

## Adding New Examples

To add a new example:

1. Create the directory structure
2. Implement your tools
3. Configure the server and client YAML files
4. Test with `mcpweaver validate`
5. Document in a README

This modular approach allows you to create focused examples for different use cases while keeping the core MCP Weaver functionality clean and reusable. 