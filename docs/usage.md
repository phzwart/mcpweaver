# Usage

## Command Line Interface

MCP Weaver provides a command-line interface for running servers and clients.

### Server Commands

```bash
# Start MCP server
mcpweaver server tools_config.yaml --host localhost --port 8080

# Validate configuration
mcpweaver validate tools_config.yaml

# Test specific tool
mcpweaver test tools_config.yaml tool_name
```

### Client Commands

```bash
# Run client with query
mcpweaver client client_config.yaml "What data is available?"

# Interactive mode
mcpweaver client client_config.yaml --interactive

# Default query
mcpweaver client client_config.yaml
```

### Example Usage

```bash
# Start file system surfer example
mcpweaver server examples/file_system_surfer/tools_config.yaml --host localhost --port 8080

# Run client
mcpweaver client examples/file_system_surfer/client_config.yaml "List files"
```
