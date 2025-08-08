"""
Utility functions for MCP Weaver.

This module provides helper functions for:
- Connecting to MCP servers
- Creating reasoning engines with automatic config detection
- Tool calling and management
"""

import requests
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
from .reasoning_engine import ReasoningEngine


def get_mcp_tools(host="localhost", port=8080) -> Optional[List[Dict[str, Any]]]:
    """Get available tools from MCP server.
    
    Args:
        host: MCP server host
        port: MCP server port
        
    Returns:
        List of available tools or None if connection failed
    """
    url = f"http://{host}:{port}/tools"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        tools = response.json()
        return tools
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to MCP server: {e}")
        return None


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any] = None, 
                  host="localhost", port=8080) -> Optional[Dict[str, Any]]:
    """Call a specific tool on the MCP server.
    
    Args:
        tool_name: Name of the tool to call
        arguments: Arguments to pass to the tool
        host: MCP server host
        port: MCP server port
        
    Returns:
        Tool execution result or None if call failed
    """
    url = f"http://{host}:{port}/"
    
    payload = {
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {}
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        print(f"Error calling tool {tool_name}: {e}")
        return None


def get_default_config_path() -> str:
    """Get the default reasoning config path from the package.
    
    Returns:
        Path to the default reasoning config file
        
    Raises:
        FileNotFoundError: If config file cannot be found
    """
    # Get the package directory
    import mcpweaver
    package_dir = Path(mcpweaver.__file__).parent.parent.parent
    
    # Look for configs in the project root
    config_path = package_dir / "configs" / "reasoning_config.yaml"
    
    if config_path.exists():
        return str(config_path)
    
    # Fallback: look for configs in the current directory
    fallback_path = Path("configs/reasoning_config.yaml")
    if fallback_path.exists():
        return str(fallback_path)
    
    raise FileNotFoundError("Could not find reasoning_config.yaml")


def create_reasoning_engine(config_path: str = None) -> ReasoningEngine:
    """Create a reasoning engine with automatic config detection.
    
    Args:
        config_path: Optional path to config file. If None, auto-detects.
        
    Returns:
        Configured ReasoningEngine instance
        
    Raises:
        FileNotFoundError: If config file cannot be found
        Exception: If engine creation fails
    """
    if config_path is None:
        config_path = get_default_config_path()
    
    try:
        engine = ReasoningEngine(config_path)
        print(f"✅ Loaded reasoning engine config from: {config_path}")
        return engine
    except Exception as e:
        print(f"❌ Error loading reasoning engine: {e}")
        raise


def quick_reasoning_engine() -> ReasoningEngine:
    """Create reasoning engine with automatic config detection (one-liner).
    
    Returns:
        Configured ReasoningEngine instance
    """
    import mcpweaver
    package_dir = Path(mcpweaver.__file__).parent.parent.parent
    config_path = package_dir / "configs" / "reasoning_config.yaml"
    return ReasoningEngine(str(config_path))


def convert_mcp_tools_to_reasoning_format(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert MCP server tools to reasoning engine format.
    
    Args:
        tools: List of tools from MCP server
        
    Returns:
        List of tools in reasoning engine format
    """
    available_tools = []
    for tool in tools:
        # Extract parameters from inputSchema
        parameters = {}
        input_schema = tool.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        for param_name, param_info in properties.items():
            parameters[param_name] = {
                "type": param_info.get("type", "Any"),
                "description": param_info.get("description", f"Parameter {param_name}"),
                "required": param_name in required
            }
        
        tool_info = {
            "name": tool["name"],
            "description": tool.get("description", "No description"),
            "parameters": parameters
        }
        available_tools.append(tool_info)
    return available_tools


# --- YAML schema validation and config versioning ---

def validate_reasoning_config(config: Dict[str, Any]) -> None:
    """Validate reasoning YAML config structure and version.
    
    Required top-level keys: llm, reasoning.
    Optional: json_schema, response_format, version.
    """
    required = ["llm", "reasoning"]
    for key in required:
        if key not in config:
            raise ValueError(f"Missing required config section: {key}")
    version = config.get("version")
    if version is not None:
        if not isinstance(version, (int, str)):
            raise ValueError("version must be int or string")
        # minimal forward-compat policy
        supported_major = 1
        try:
            major = int(str(version).split(".")[0])
            if major > supported_major:
                raise ValueError(f"Config version {version} not supported (max {supported_major}.x)")
        except Exception:
            # non-numeric ok; ignore
            pass


def load_reasoning_config(config_path: str) -> Dict[str, Any]:
    """Load and validate reasoning config from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    data = path.read_text()
    config = yaml.safe_load(data)
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a YAML mapping")
    validate_reasoning_config(config)
    return config
