# mcpweaver

![PyPI version](https://img.shields.io/pypi/v/mcpweaver.svg)
[![Documentation Status](https://readthedocs.org/projects/mcpweaver/badge/?version=latest)](https://mcpweaver.readthedocs.io/en/latest/?version=latest)

Lightweight YAML configureable MCP Server / Client tools

* PyPI package: https://pypi.org/project/mcpweaver/
* Free software: MIT License
* Documentation: https://mcpweaver.readthedocs.io.

## Features

* **Generic MCP Server**: Load tools directly from YAML configuration
* **LLM Client**: Configurable client that connects to MCP servers
* **YAML Configuration**: All behavior configurable via YAML files
* **Tool Chaining**: Build sequences of tool calls with argument extraction
* **FastAPI Integration**: Modern web API for MCP server
* **CLI Interface**: Easy-to-use command line tools

## Installation

```bash
pip install mcpweaver
```

## Command Line Usage

### MCP Server Commands

```bash
# Start MCP server
mcpweaver server tools_config.yaml --host localhost --port 8080

# Validate YAML configuration
mcpweaver validate tools_config.yaml

# Test a specific tool
mcpweaver test tools_config.yaml tool_name
```

### MCP Client Commands

```bash
# Run client with query
mcpweaver client client_config.yaml "What data is available?"

# Run in interactive mode
mcpweaver client client_config.yaml --interactive

# Run with default query
mcpweaver client client_config.yaml
```

### Initialize Examples

```bash
# Create example configuration files
mcpweaver init --output ./examples

# Show configuration information
mcpweaver info config.yaml
```

## Quick Start

### Using the File System Surfer Example

```bash
# Start the server
mcpweaver server examples/file_system_surfer/tools_config.yaml --host localhost --port 8080

# Run the client
mcpweaver client examples/file_system_surfer/client_config.yaml "List files in the current directory"
```

## Configuration Examples

### Server Configuration (tools_config.yaml)

```yaml
tools:
  list_files:
    python_path: "file_tools.list_files"
    full_path: "examples/file_system_surfer/tools"  # Directory to add to Python path
    workflow_context:
      description: "List files in a directory"
  
  read_file:
    python_path: "file_tools.read_file"
    full_path: "examples/file_system_surfer/tools"
    workflow_context:
      description: "Read file contents"
```

### Client Configuration (client_config.yaml)

```yaml
llm:
  model: "phi3:mini"
  provider: "ollama"

mcp_server:
  host: "localhost"
  port: 8080
  timeout: 10

behavior:
  instructions: "You are a helpful assistant that uses tools to answer questions."

tools:
  list_files:
    description: "List files in a directory"
    keywords: ["list", "files", "directory"]
```

## Development

### Setup

```bash
git clone https://github.com/phzwart/mcpweaver.git
cd mcpweaver
pip install -e ".[test]"
```

### Running Tests

```bash
pytest
```

## Credits

This package was created with [Cookiecutter](https://github.com/audreyfeldroy/cookiecutter) and the [audreyfeldroy/cookiecutter-pypackage](https://github.com/audreyfeldroy/cookiecutter-pypackage) project template.
