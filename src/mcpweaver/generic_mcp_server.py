"""
Generic MCP Server that reads YAML configuration and creates an MCP server directly.

Usage:
    python generic_mcp_server.py <yaml_config.yaml> [--host localhost] [--port 8080]
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
import importlib
import inspect
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from .conversion_manager import ConversionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_tool_context(tools: List[Dict[str, Any]], query: str = None) -> str:
    """Generate context about how tools work together.
    
    This function lives inside the main MCP server and analyzes
    the available tools to generate helpful context for reasoning.
    
    Args:
        tools: List of available tools with their definitions
        query: Optional user query to analyze
        
    Returns:
        Context string about tool relationships and usage patterns
    """
    context_parts = []
    
    # Analyze tool categories
    numpy_tools = [t for t in tools if t['name'].startswith('np_')]
    torch_tools = [t for t in tools if t['name'].startswith('torch_')]
    
    # Generate category-specific context
    if numpy_tools:
        context_parts.append("Numpy tools are for numerical computations on arrays:")
        for tool in numpy_tools:
            context_parts.append(f"- {tool['name']}: {tool.get('description', 'No description')}")
    
    if torch_tools:
        context_parts.append("PyTorch tools are for tensor operations:")
        for tool in torch_tools:
            context_parts.append(f"- {tool['name']}: {tool.get('description', 'No description')}")
    
    # Generate workflow patterns
    if numpy_tools and torch_tools:
        context_parts.append("\nCommon workflows:")
        context_parts.append("- Use torch_tensor to create tensors from arrays")
        context_parts.append("- Use torch_mean for tensor operations")
        context_parts.append("- Use np_* functions for array operations")
    
    # Query-specific context
    if query:
        context_parts.append(f"\nQuery analysis: {query}")
        if 'mean' in query.lower():
            context_parts.append("- Consider np_mean for arrays or torch_mean for tensors")
        if 'std' in query.lower() or 'sigma' in query.lower():
            context_parts.append("- Use np_std for standard deviation calculations")
        if 'sum' in query.lower():
            context_parts.append("- Use np_sum for array summation")
    
    return "\n".join(context_parts)


class GenericMCPServer:
    """Generic MCP server that loads tools from YAML configuration."""
    
    def __init__(self, config_path: str):
        """Initialize the server with configuration file path."""
        self.config_path = Path(config_path)
        self.config = {}
        self.tools = {}
        self.conversion_manager = None
        
        self.load_configuration()
    
    def load_configuration(self) -> None:
        """Load tools from YAML configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Load serialization configuration and initialize conversion manager
        serialization_config = self.config.get('serialization', {})
        conversions_file = serialization_config.get('conversions_file')
        logger.info(f"Serialization config: {serialization_config}")
        logger.info(f"Conversions file: {conversions_file}")
        
        if conversions_file:
            # Resolve relative path from config file location
            config_dir = self.config_path.parent
            conversions_path = config_dir / conversions_file
            logger.info(f"Looking for conversions file at: {conversions_path}")
            if conversions_path.exists():
                logger.info(f"Conversions file found, loading...")
                self.conversion_manager = ConversionManager(str(conversions_path))
            else:
                logger.warning(f"Conversions file not found: {conversions_path}")
                self.conversion_manager = ConversionManager()
        else:
            logger.info("No conversions file specified, using default conversion manager")
            self.conversion_manager = ConversionManager()
        
        tools_config = self.config.get('tools', {})
        
        for tool_name, tool_config in tools_config.items():
            python_path = tool_config.get('python_path', '')
            workflow_context = tool_config.get('workflow_context', {})
            full_path = tool_config.get('full_path', None)  # Optional full path for imports
            
            # Load the function directly
            if full_path:
                func = self._import_function_with_path(python_path, full_path)
            else:
                func = self._import_function(python_path)
            
            # Create tool info
            tool_info = {
                'name': tool_name,
                'python_path': python_path,
                'func': func,
                'workflow_context': workflow_context,
                'description': self._extract_description(func),
                'signature': self._extract_signature(func),
                'parameters': self._extract_parameters_from_yaml(workflow_context) or self._extract_parameters(func)
            }
            
            self.tools[tool_name] = tool_info
            logger.info(f"Loaded tool: {tool_name} -> {python_path}")
    
    def _import_function(self, python_path: str):
        """Import function from Python path."""
        try:
            if '.' in python_path:
                module_path, func_name = python_path.rsplit('.', 1)
                
                # Regular function import - no hardcoded logic
                module = importlib.import_module(module_path)
                return getattr(module, func_name)
            else:
                raise ValueError(f"Invalid Python path: {python_path}")
        except Exception as e:
            raise ValueError(f"Could not import {python_path}: {e}")
    
    def _import_function_with_path(self, python_path: str, full_path: str = None):
        """Import function from Python path with optional full path injection."""
        try:
            if full_path:
                # Use the full path directly
                import sys
                import os
                if full_path not in sys.path:
                    sys.path.insert(0, full_path)
            
            if '.' in python_path:
                module_path, func_name = python_path.rsplit('.', 1)
                
                # Regular function import
                module = importlib.import_module(module_path)
                return getattr(module, func_name)
            else:
                raise ValueError(f"Invalid Python path: {python_path}")
        except Exception as e:
            raise ValueError(f"Could not import {python_path}: {e}")
    
    def _extract_description(self, func) -> str:
        """Extract description from function docstring."""
        if func.__doc__:
            # Get first line of docstring
            lines = func.__doc__.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('WORKFLOW CONTEXT:'):
                    return line
        return "No description available"
    
    def _extract_parameters(self, func) -> Dict[str, Dict[str, Any]]:
        """Extract parameter information from function signature and docstring."""
        import inspect
        
        try:
            # Get function signature
            sig = inspect.signature(func)
            parameters = {}
            
            # Extract parameter info from signature
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                    
                param_info = {
                    'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                    'default': str(param.default) if param.default != inspect.Parameter.empty else None,
                    'required': param.default == inspect.Parameter.empty
                }
                
                # Try to get description from docstring
                if func.__doc__:
                    import re
                    # Look for Args section in docstring
                    args_match = re.search(r'Args:\s*\n(.*?)(?:\n\n|\n[A-Z]|$)', func.__doc__, re.DOTALL)
                    if args_match:
                        args_section = args_match.group(1)
                        # Look for this specific parameter
                        param_match = re.search(rf'{param_name}:\s*(.*?)(?:\n|$)', args_section)
                        if param_match:
                            param_info['description'] = param_match.group(1).strip()
                        else:
                            param_info['description'] = f"Parameter {param_name}"
                    else:
                        param_info['description'] = f"Parameter {param_name}"
                else:
                    param_info['description'] = f"Parameter {param_name}"
                
                parameters[param_name] = param_info
            
            return parameters
            
        except ValueError as e:
            # Handle built-in methods that don't have inspectable signatures
            if "no signature found for builtin" in str(e):
                # For built-in methods, return basic parameter info
                parameters = {}
                
                # Try to get basic info from docstring
                if func.__doc__:
                    import re
                    # Look for Args section in docstring
                    args_match = re.search(r'Args:\s*\n(.*?)(?:\n\n|\n[A-Z]|$)', func.__doc__, re.DOTALL)
                    if args_match:
                        args_section = args_match.group(1)
                        # Extract parameter names and descriptions
                        param_matches = re.findall(r'(\w+):\s*(.*?)(?:\n|$)', args_section)
                        for param_name, description in param_matches:
                            parameters[param_name] = {
                                'type': 'Any',
                                'default': None,
                                'required': True,
                                'description': description.strip()
                            }
                
                # If no docstring info, return empty dict
                return parameters
            else:
                # Re-raise other ValueError exceptions
                raise
    
    def _extract_signature(self, func) -> str:
        """Extract function signature, handling built-in methods gracefully."""
        try:
            return str(inspect.signature(func))
        except ValueError as e:
            # Handle built-in methods that don't have inspectable signatures
            if "no signature found for builtin" in str(e):
                return "(built-in method - signature not available)"
            else:
                # Re-raise other ValueError exceptions
                raise
    
    def _extract_parameters_from_yaml(self, workflow_context: Dict[str, Any]) -> Optional[Dict[str, Dict[str, Any]]]:
        """Extract parameter information from YAML workflow_context if defined."""
        if not workflow_context or 'parameters' not in workflow_context:
            return None
        
        parameters = {}
        yaml_params = workflow_context['parameters']
        
        for param_name, param_description in yaml_params.items():
            parameters[param_name] = {
                'type': 'Any',
                'default': None,
                'required': True,
                'description': param_description
            }
        
        return parameters
    
    def _convert_python_type_to_json_schema(self, python_type: str) -> Dict[str, Any]:
        """Convert Python type annotation to JSON Schema type.
        
        Args:
            python_type: Python type annotation string
            
        Returns:
            JSON Schema type definition
        """
        # Handle common Python types
        if python_type in ['int', 'integer']:
            return {"type": "integer"}
        elif python_type in ['float', 'number']:
            return {"type": "number"}
        elif python_type in ['bool', 'boolean']:
            return {"type": "boolean"}
        elif python_type in ['str', 'string']:
            return {"type": "string"}
        elif python_type in ['list', 'List', 'array']:
            return {"type": "array", "items": {"type": "string"}}
        elif python_type in ['dict', 'Dict', 'object']:
            return {"type": "object"}
        elif python_type == 'Any':
            return {"type": "string"}  # Default to string for Any
        else:
            # For complex types or unknown types, default to string
            return {"type": "string"}

    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Get list of tools in MCP format with proper JSON schemas."""
        tools_list = []
        
        for tool_name, tool_info in self.tools.items():
            # Build input schema from extracted parameters
            properties = {}
            required = []
            
            for param_name, param_info in tool_info['parameters'].items():
                # Convert Python type to JSON Schema type
                param_type = param_info.get('type', 'Any')
                json_schema_type = self._convert_python_type_to_json_schema(param_type)
                
                # Add description
                json_schema_type["description"] = param_info.get('description', f"Parameter {param_name}")
                
                # Add default value if available
                if param_info.get('default') is not None:
                    json_schema_type["default"] = param_info['default']
                
                properties[param_name] = json_schema_type
                
                # Add to required array if parameter is required
                if param_info.get('required', False):
                    required.append(param_name)
            
            # Build the complete tool definition
            tool_dict = {
                "name": tool_name,
                "description": tool_info['description'],
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                },
                "outputSchema": {"type": "object"},
                "parameters": tool_info['parameters']  # Keep for backwards compatibility
            }
            tools_list.append(tool_dict)
        
        return tools_list
    
    def serialize_result(self, result: Any, tool_name: str = None) -> Any:
        """Serialize result to JSON-safe format."""
        try:
            logger.info(f"Serializing result of type: {type(result)}")
            
            # Use conversion manager for serialization if available
            if self.conversion_manager:
                logger.info("Using conversion manager for serialization")
                # Use the actual tool name if available, otherwise use a generic approach
                tool_name_for_serialization = tool_name if tool_name else "unknown_tool"
                serialized = self.conversion_manager.serialize_value(result, tool_name_for_serialization)
                logger.info(f"Conversion manager returned: {type(serialized)}")
                return serialized
            
            # Handle NumPy arrays directly if conversion manager is not available
            if hasattr(result, 'tolist'):
                logger.info("Converting NumPy array to list")
                return result.tolist()
            elif hasattr(result, 'dtype'):
                logger.info("Converting NumPy object to list")
                return result.tolist()
            
            # Fallback to direct serialization
            import json
            json.dumps(result)
            logger.info("Direct JSON serialization successful")
            return result
        except (TypeError, ValueError) as e:
            logger.error(f"Serialization error: {e}")
            # If direct serialization fails, convert to string representation
            try:
                return str(result)
            except:
                return f"<Non-serializable object of type {type(result).__name__}>"
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool with arguments."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        tool_info = self.tools[tool_name]
        func = tool_info['func']
        
        # Convert arguments for NumPy functions on the server side
        if self.conversion_manager:
            arguments = self.conversion_manager.convert_arguments(tool_name, arguments)
        
        try:
            # For built-in methods, skip signature inspection
            func_type = str(type(func))
            logger.info(f"Tool '{tool_name}' function type: {func_type}")
            
            # Check for built-in method patterns
            is_builtin = ("builtin_function_or_method" in func_type or 
                         "built-in method" in func_type or 
                         "numpy.random" in func_type or 
                         "RandomState" in func_type or
                         "numpy._ArrayFunctionDispatcher" in func_type or
                         "numpy.ufunc" in func_type)
            
            if is_builtin:
                logger.info(f"Detected built-in method for '{tool_name}', skipping signature inspection")
                # Call function directly with arguments
                if arguments:
                    result = func(**arguments)
                else:
                    result = func()
            else:
                logger.info(f"Regular function for '{tool_name}', using signature inspection")
                # Get function signature to check required arguments
                import inspect
                try:
                    sig = inspect.signature(func)
                    required_params = [name for name, param in sig.parameters.items() 
                                     if param.default == inspect.Parameter.empty and param.kind != inspect.Parameter.VAR_POSITIONAL]
                    
                    # Check if required arguments are missing
                    if required_params and not arguments:
                        missing_args = ", ".join(required_params)
                        raise ValueError(f"Tool '{tool_name}' requires arguments: {missing_args}")
                    
                    # Call function with arguments if provided, otherwise call without args
                    if arguments:
                        result = func(**arguments)
                    else:
                        result = func()
                except ValueError as e:
                    # If signature inspection fails, try calling directly
                    logger.warning(f"Signature inspection failed for '{tool_name}': {e}, trying direct call")
                    if arguments:
                        result = func(**arguments)
                    else:
                        result = func()
            
            # Serialize result to ensure it's JSON-safe
            serialized_result = self.serialize_result(result, tool_name)
            logger.info(f"Successfully executed tool '{tool_name}'")
            return serialized_result
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            raise
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a tool."""
        if tool_name not in self.tools:
            return None
        
        tool_info = self.tools[tool_name]
        return {
            "name": tool_name,
            "python_path": tool_info['python_path'],
            "signature": tool_info['signature'],
            "description": tool_info['description'],
            "workflow_context": tool_info['workflow_context'],
            "parameters": tool_info['parameters']
        }

def create_fastapi_app(server: GenericMCPServer) -> FastAPI:
    """Create FastAPI app with MCP endpoints."""
    app = FastAPI(title="Generic MCP Server", version="1.0.0")
    
    @app.post("/")
    async def handle_mcp_request(request: Dict[str, Any]):
        """Handle MCP JSON-RPC requests."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "tools/list":
                result = server.get_tools_list()
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = server.execute_tool(tool_name, arguments)
            elif method == "tools/get_info":
                tool_name = params.get("name")
                result = server.get_tool_info(tool_name)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
            )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "tools": len(server.tools)}
    
    @app.get("/tools")
    async def list_tools():
        """List available tools."""
        return server.get_tools_list()
    
    return app

def validate_config(config_path: str) -> bool:
    """Validate YAML configuration file."""
    try:
        server = GenericMCPServer(config_path)
        print(f"✅ Configuration file '{config_path}' is valid")
        print(f"📦 Loaded {len(server.tools)} tools:")
        
        for tool_name, tool_info in server.tools.items():
            print(f"  - {tool_name} ({tool_info['python_path']})")
            print(f"    Description: {tool_info['description']}")
            print(f"    Signature: {tool_info['signature']}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration file '{config_path}' is invalid: {e}")
        return False

def test_tool(config_path: str, tool_name: str) -> bool:
    """Test a specific tool."""
    try:
        server = GenericMCPServer(config_path)
        
        if tool_name not in server.tools:
            print(f"❌ Tool '{tool_name}' not found")
            return False
        
        print(f"🧪 Testing tool '{tool_name}'...")
        result = server.execute_tool(tool_name, {})
        print(f"✅ Tool executed successfully")
        print(f"📊 Result: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool test failed: {e}")
        return False

def run_server(config_path: str, host: str = "localhost", port: int = 8080, verbose: bool = False):
    """Run the FastAPI server."""
    server = GenericMCPServer(config_path)
    app = create_fastapi_app(server)
    
    logger.info(f"🚀 Generic MCP Server running on {host}:{port}")
    logger.info(f"📁 Configuration: {config_path}")
    logger.info(f"📦 Loaded {len(server.tools)} tools:")
    
    if verbose:
        logger.info("🔍 Full MCP Tool Definitions:")
        for tool_name, tool_info in server.tools.items():
            logger.info(f"\n📋 Tool: {tool_name}")
            logger.info(f"   Python Path: {tool_info['python_path']}")
            logger.info(f"   Description: {tool_info['description']}")
            logger.info(f"   Signature: {tool_info['signature']}")
            logger.info(f"   Workflow Context: {tool_info['workflow_context']}")
            logger.info(f"   Parameters:")
            for param_name, param_info in tool_info['parameters'].items():
                logger.info(f"     {param_name}:")
                logger.info(f"       Type: {param_info.get('type', 'Any')}")
                logger.info(f"       Required: {param_info.get('required', False)}")
                logger.info(f"       Default: {param_info.get('default', 'None')}")
                logger.info(f"       Description: {param_info.get('description', 'No description')}")
            
            # Show MCP-compatible tool definition
            mcp_tool = {
                "name": tool_name,
                "description": tool_info['description'],
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        param_name: {
                            "type": param_info.get('type', 'string'),
                            "description": param_info.get('description', f"Parameter {param_name}")
                        }
                        for param_name, param_info in tool_info['parameters'].items()
                    },
                    "required": [
                        param_name for param_name, param_info in tool_info['parameters'].items()
                        if param_info.get('required', False)
                    ]
                }
            }
            logger.info(f"   MCP Definition: {json.dumps(mcp_tool, indent=2)}")
    else:
        for tool_name in server.tools.keys():
            logger.info(f"  - {tool_name}")
    
    uvicorn.run(app, host=host, port=port)

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python generic_mcp_server.py <yaml_config.yaml> [--host localhost] [--port 8080] [--verbose]")
        print("Commands:")
        print("  validate <yaml_file>  - Validate YAML configuration")
        print("  test <yaml_file> <tool_name>  - Test a specific tool")
        print("  server <yaml_file> [--host host] [--port port] [--verbose]  - Run MCP server")
        return
    
    command = sys.argv[1]
    
    if command == "validate":
        if len(sys.argv) < 3:
            print("❌ YAML file required for validate command")
            return
        config_path = sys.argv[2]
        success = validate_config(config_path)
        sys.exit(0 if success else 1)
    
    elif command == "test":
        if len(sys.argv) < 4:
            print("❌ YAML file and tool name required for test command")
            return
        config_path = sys.argv[2]
        tool_name = sys.argv[3]
        success = test_tool(config_path, tool_name)
        sys.exit(0 if success else 1)
    
    elif command == "server":
        if len(sys.argv) < 3:
            print("❌ YAML file required for server command")
            return
        config_path = sys.argv[2]
        
        # Parse optional arguments
        host = "localhost"
        port = 8080
        verbose = False
        
        for i, arg in enumerate(sys.argv[3:], 3):
            if arg == "--host" and i + 1 < len(sys.argv):
                host = sys.argv[i + 1]
            elif arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
            elif arg == "--verbose":
                verbose = True
        
        try:
            run_server(config_path, host, port, verbose)
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: validate, test, server")

if __name__ == "__main__":
    main() 