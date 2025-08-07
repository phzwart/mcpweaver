"""
Schema Generator for MCP Weaver
Generates JSON schemas dynamically from MCP server tool information.
"""

import requests
from typing import Dict, Any, List, Optional


class SchemaGenerator:
    """Generates JSON schemas from MCP server tool information."""
    
    def __init__(self, mcp_server_url: str, timeout: int = 10):
        """Initialize the schema generator.
        
        Args:
            mcp_server_url: URL of the MCP server
            timeout: Request timeout in seconds
        """
        self.mcp_server_url = mcp_server_url
        self.timeout = timeout
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP server."""
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
                raise Exception(f"HTTP error: {response.status_code}")
                
        except Exception as e:
            raise Exception(f"Error getting tools: {e}")
    
    def get_tool_info_from_server(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed tool information from the server."""
        try:
            response = requests.post(
                self.mcp_server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/get_info",
                    "params": {
                        "name": tool_name
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("result")
            
            return None
            
        except Exception as e:
            print(f"⚠️  Could not get tool info for {tool_name}: {e}")
            return None
    
    def _convert_python_type_to_json(self, python_type: str) -> str:
        """Convert Python type annotations to JSON schema types."""
        type_mapping = {
            'str': 'string',
            'string': 'string',
            'int': 'integer',
            'integer': 'integer',
            'float': 'number',
            'number': 'number',
            'bool': 'boolean',
            'boolean': 'boolean',
            'list': 'array',
            'array': 'array',
            'dict': 'object',
            'object': 'object',
            'Any': 'string',  # Default to string for unknown types
            'typing.Any': 'string'
        }
        
        # Clean up the type string
        clean_type = python_type.replace('typing.', '').replace('numpy.', '').replace('np.', '')
        
        return type_mapping.get(clean_type, 'string')
    
    def generate_json_schema(self) -> Optional[Dict[str, Any]]:
        """Generate JSON schema dynamically from MCP server tool information."""
        try:
            # Get tools from server
            tools = self.get_available_tools()
            
            if not tools:
                print("⚠️  No tools available from server")
                return None
            
            # Build schema properties
            tool_names = [tool['name'] for tool in tools]
            argument_properties = {}
            
            for tool in tools:
                tool_name = tool['name']
                # Get detailed tool info including parameters
                tool_info = self.get_tool_info_from_server(tool_name)
                
                if tool_info and 'parameters' in tool_info:
                    # Build argument schema for this tool
                    arg_schema = {
                        "type": "object",
                        "properties": {}
                    }
                    
                    required_params = []
                    
                    for param_name, param_info in tool_info['parameters'].items():
                        param_type = param_info.get('type', 'string')
                        description = param_info.get('description', f'Parameter {param_name}')
                        required = param_info.get('required', False)
                        
                        # Convert Python types to JSON schema types
                        json_type = self._convert_python_type_to_json(param_type)
                        
                        arg_schema["properties"][param_name] = {
                            "type": json_type,
                            "description": description
                        }
                        
                        if required:
                            required_params.append(param_name)
                    
                    if required_params:
                        arg_schema["required"] = required_params
                    
                    argument_properties[tool_name] = arg_schema
                else:
                    # Fallback for tools without detailed parameter info
                    argument_properties[tool_name] = {
                        "type": "object",
                        "properties": {},
                        "description": f"Arguments for {tool_name}"
                    }
            
            # Build the complete schema
            schema = {
                "type": "object",
                "properties": {
                    "tools": {
                        "type": "array",
                        "items": {"type": "string", "enum": tool_names},
                        "description": "List of tool names to use"
                    },
                    "arguments": {
                        "type": "object",
                        "properties": argument_properties,
                        "additionalProperties": False,
                        "description": "Arguments for each tool"
                    }
                },
                "required": ["tools", "arguments"]
            }
            
            print(f"✅ Generated JSON schema with {len(tool_names)} tools")
            return schema
            
        except Exception as e:
            print(f"⚠️  Could not generate schema from server: {e}")
            return None


def generate_schema_from_server(mcp_server_url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """Convenience function to generate schema from server."""
    generator = SchemaGenerator(mcp_server_url, timeout)
    return generator.generate_json_schema() 