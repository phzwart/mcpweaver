"""Conversion Manager for handling array type conversions in MCP workflows."""

import yaml
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ConversionManager:
    """Manages array type conversions based on external configuration."""
    
    def __init__(self, conversions_file: Optional[str] = None):
        """Initialize the conversion manager.
        
        Args:
            conversions_file: Path to the conversions configuration file
        """
        self.conversions_file = conversions_file
        self.conversions_config = {}
        self.settings = {}
        self.error_handling = {}
        
        if conversions_file:
            self.load_conversions(conversions_file)
        else:
            # Use default conversions file from the package
            import os
            package_dir = os.path.dirname(os.path.abspath(__file__))
            default_conversions_file = os.path.join(package_dir, "conversions.yaml")
            if os.path.exists(default_conversions_file):
                self.load_conversions(default_conversions_file)
            else:
                logger.warning("No conversions file provided and default file not found")
    
    def load_conversions(self, conversions_file: str) -> None:
        """Load conversion configuration from file.
        
        Args:
            conversions_file: Path to the conversions configuration file
        """
        try:
            config_path = Path(conversions_file)
            if not config_path.exists():
                logger.warning(f"Conversions file not found: {conversions_file}")
                return
            
            with open(config_path, 'r') as f:
                self.conversions_config = yaml.safe_load(f)
            
            self.settings = self.conversions_config.get('settings', {})
            self.error_handling = self.conversions_config.get('error_handling', {})
            
            logger.info(f"Loaded conversions from: {conversions_file}")
            
        except Exception as e:
            logger.error(f"Error loading conversions file: {e}")
    
    def get_conversion_for_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get conversion configuration for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Conversion configuration for the tool, or None if not found
        """
        conversions = self.conversions_config.get('conversions', {})
        
        for array_type, config in conversions.items():
            tool_prefixes = config.get('tool_prefixes', [])
            for prefix in tool_prefixes:
                if tool_name.startswith(prefix):
                    return config
        
        return None
    
    def should_convert_argument(self, tool_name: str, arg_name: str) -> bool:
        """Check if an argument should be converted for a tool.
        
        Args:
            tool_name: Name of the tool
            arg_name: Name of the argument
            
        Returns:
            True if the argument should be converted
        """
        conversion_config = self.get_conversion_for_tool(tool_name)
        if not conversion_config:
            return False
        
        argument_mapping = self.conversions_config.get('argument_mapping', {})
        array_type = None
        
        # Find the array type for this tool
        conversions = self.conversions_config.get('conversions', {})
        for type_name, config in conversions.items():
            tool_prefixes = config.get('tool_prefixes', [])
            for prefix in tool_prefixes:
                if tool_name.startswith(prefix):
                    array_type = type_name
                    break
            if array_type:
                break
        
        if not array_type:
            return False
        
        # Check if this argument should be converted
        mapping = argument_mapping.get(array_type, {})
        array_arguments = mapping.get('array_arguments', [])
        
        return arg_name in array_arguments
    
    def serialize_value(self, value: Any, tool_name: str) -> Any:
        """Serialize a value for JSON transmission.
        
        Args:
            value: The value to serialize
            tool_name: Name of the tool (for context)
            
        Returns:
            Serialized value
        """
        logger.info(f"ConversionManager: Serializing value of type {type(value)} for tool {tool_name}")
        
        conversion_config = self.get_conversion_for_tool(tool_name)
        if not conversion_config:
            logger.info(f"ConversionManager: No conversion config found for {tool_name}")
            return value
        
        serialize_config = conversion_config.get('serialize', {})
        if not serialize_config.get('enabled', False):
            logger.info(f"ConversionManager: Serialization disabled for {tool_name}")
            return value
        
        try:
            method = serialize_config.get('method', 'tolist')
            logger.info(f"ConversionManager: Using method '{method}' for {tool_name}")
            
            if method == 'tolist' and hasattr(value, 'tolist'):
                logger.info(f"ConversionManager: Converting to list using tolist()")
                result = value.tolist()
                logger.info(f"ConversionManager: Result type: {type(result)}")
                return result
            elif method == 'to_dict' and hasattr(value, 'to_dict'):
                logger.info(f"ConversionManager: Converting to dict using to_dict()")
                return value.to_dict()
            else:
                logger.info(f"ConversionManager: No conversion method available, returning as-is")
                return value
                
        except Exception as e:
            logger.error(f"ConversionManager: Error serializing value for {tool_name}: {e}")
            failure_behavior = self.error_handling.get('on_serialization_failure', 'string')
            
            if failure_behavior == 'error':
                raise
            elif failure_behavior == 'string':
                return str(value)
            else:  # pass_through
                return value
    
    def deserialize_value(self, value: Any, tool_name: str, arg_name: str) -> Any:
        """Deserialize a value for tool execution.
        
        Args:
            value: The value to deserialize
            tool_name: Name of the tool
            arg_name: Name of the argument
            
        Returns:
            Deserialized value
        """
        if not self.should_convert_argument(tool_name, arg_name):
            return value
        
        conversion_config = self.get_conversion_for_tool(tool_name)
        if not conversion_config:
            return value
        
        deserialize_config = conversion_config.get('deserialize', {})
        if not deserialize_config.get('enabled', False):
            return value
        
        try:
            method = deserialize_config.get('method', '')
            array_creator = conversion_config.get('array_creator', '')
            
            if not isinstance(value, list):
                return value
            
            # Import the required library
            import_statement = conversion_config.get('import', '')
            if import_statement:
                # Execute import in the current namespace
                exec(import_statement, globals())
            
            # Create the array/tensor
            if array_creator:
                # Parse the array creator (e.g., "np.array" -> np.array)
                if '.' in array_creator:
                    module_name, func_name = array_creator.split('.', 1)
                    # Get the module from globals
                    module = globals().get(module_name)
                    if module:
                        creator_func = getattr(module, func_name)
                        return creator_func(value)
                    else:
                        raise ImportError(f"Module {module_name} not found")
                else:
                    creator_func = globals().get(array_creator)
                    if creator_func:
                        return creator_func(value)
                    else:
                        raise NameError(f"Function {array_creator} not found")
            else:
                return value
                
        except Exception as e:
            logger.error(f"Error deserializing value for {tool_name}.{arg_name}: {e}")
            failure_behavior = self.error_handling.get('on_deserialization_failure', 'pass_through')
            
            if failure_behavior == 'error':
                raise
            elif failure_behavior == 'string':
                return str(value)
            else:  # pass_through
                return value
    
    def convert_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert arguments for a tool based on conversion configuration.
        
        Args:
            tool_name: Name of the tool
            arguments: Arguments to convert
            
        Returns:
            Converted arguments
        """
        if not self.settings.get('enabled', False):
            return arguments
        
        converted_args = {}
        
        for arg_name, arg_value in arguments.items():
            if self.should_convert_argument(tool_name, arg_name):
                converted_args[arg_name] = self.deserialize_value(arg_value, tool_name, arg_name)
            else:
                converted_args[arg_name] = arg_value
        
        return converted_args 