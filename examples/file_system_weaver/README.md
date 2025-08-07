# File System Surfer Example

This example demonstrates how to use MCP Weaver with file system tools.

## Features

- **List Files**: Browse directories and find files
- **Read Files**: View file contents with line limits
- **Count Lines**: Analyze file structure (total, empty, code lines)
- **Get File Info**: Detailed file metadata and statistics
- **Search Files**: Find files by pattern or content

## Usage

### Start the Server

**Important**: Run from the project root directory (where `examples/` is located):

```bash
# From the project root directory
mcpweaver server examples/file_system_weaver/tools_config.yaml --host localhost --port 8080
```

### Run the Client

**Important**: Run from the project root directory (where `examples/` is located):

```bash
# Interactive mode
mcpweaver client examples/file_system_weaver/client_config.yaml --interactive

# Single query
mcpweaver client examples/file_system_weaver/client_config.yaml "List files in the current directory"

# Read a specific file
mcpweaver client examples/file_system_weaver/client_config.yaml "Read the README.md file"

# Count lines in a file
mcpweaver client examples/file_system_weaver/client_config.yaml "Count lines in pyproject.toml"
```

## Configuration

- **Server Config**: `tools_config.yaml` - Defines the file system tools with full path injection
- **Client Config**: `client_config.yaml` - Configures the LLM client behavior
- **Tools**: `tools/` - Contains the file system tool implementations

### Tool Configuration

The tools use `full_path` injection to handle imports from any directory:

```yaml
tools:
  list_files:
    python_path: "file_tools.list_files"
    full_path: "examples/file_system_weaver/tools"  # Directory to add to Python path
    workflow_context:
      description: "List files in a directory"
```

## Example Queries

- "What files are in this directory?"
- "Read the README file"
- "Count lines in the main Python file"
- "Search for files containing 'config'"
- "Get information about the largest file" 