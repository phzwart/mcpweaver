"""Conversion Manager for handling array type conversions in MCP workflows."""

import yaml
import logging
import importlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
        self.settings: Dict[str, Any] = {}
        self.error_handling: Dict[str, Any] = {}
        # Caches for faster lookups/safer imports
        self._prefix_to_type: Dict[str, str] = {}
        self._module_cache: Dict[str, Any] = {}
        self._callable_cache: Dict[str, Any] = {}
        
        if conversions_file:
            self.load_conversions(conversions_file)
        else:
            # Resolve default conversions file with precedence:
            # 1) Env var MCPWEAVER_CONVERSIONS_FILE
            # 2) Project configs/conversions.yaml
            # 3) Legacy src/mcpweaver/conversions.yaml
            try:
                from pathlib import Path
                env_path = os.environ.get("MCPWEAVER_CONVERSIONS_FILE")
                if env_path and Path(env_path).exists():
                    self.load_conversions(env_path)
                    return
                import mcpweaver
                project_root = Path(mcpweaver.__file__).parent.parent.parent
                configs_file = project_root / "configs" / "conversions.yaml"
                if configs_file.exists():
                    self.load_conversions(str(configs_file))
                else:
                    # Legacy fallback: src/mcpweaver/conversions.yaml
                    legacy_file = Path(__file__).parent / "conversions.yaml"
                    if legacy_file.exists():
                        self.load_conversions(str(legacy_file))
                    else:
                        logger.warning("No conversions file provided and no default found in env, configs/, or legacy location")
            except Exception as e:
                logger.warning("Failed to resolve default conversions file: %s", e)
    
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

            # Build prefix → array type map for O(1) lookup
            self._prefix_to_type.clear()
            for array_type, cfg in self.conversions_config.get('conversions', {}).items():
                for prefix in cfg.get('tool_prefixes', []):
                    self._prefix_to_type[prefix] = array_type
            
            logger.debug("Loaded conversions from: %s", conversions_file)
            
        except Exception as e:
            logger.error(f"Error loading conversions file: {e}")
    
    def _get_array_type_for_tool(self, tool_name: str) -> Optional[str]:
        """Return the array type key (e.g., 'numpy', 'pytorch', 'pandas') for a tool name."""
        for prefix, array_type in self._prefix_to_type.items():
            if tool_name.startswith(prefix):
                return array_type
        return None

    def get_conversion_for_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get conversion configuration for a specific tool."""
        array_type = self._get_array_type_for_tool(tool_name)
        if not array_type:
            return None
        return self.conversions_config.get('conversions', {}).get(array_type)
    
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
        array_type = self._get_array_type_for_tool(tool_name)
        if not array_type:
            return False
        mapping = self.conversions_config.get('argument_mapping', {}).get(array_type, {})
        return arg_name in (mapping.get('array_arguments', []) or [])
    
    def serialize_value(self, value: Any, tool_name: str) -> Any:
        """Serialize a value for JSON transmission.
        
        Args:
            value: The value to serialize
            tool_name: Name of the tool (for context)
            
        Returns:
            Serialized value
        """
        logger.debug("Serializing value of type %s for tool %s", type(value), tool_name)

        conversion_config = self.get_conversion_for_tool(tool_name)
        if not conversion_config:
            logger.debug("No conversion config found for %s", tool_name)
            return value

        serialize_config = conversion_config.get('serialize', {})
        if not serialize_config.get('enabled', False):
            logger.debug("Serialization disabled for %s", tool_name)
            return value

        try:
            method = serialize_config.get('method', '')
            list_converter = conversion_config.get('list_converter')
            # Prefer explicit method, fallback to available attributes
            if method == 'tolist' and hasattr(value, 'tolist'):
                return value.tolist()
            if method == 'to_dict' and hasattr(value, 'to_dict'):
                return value.to_dict()
            # Fallback to configured list converter if present
            if list_converter and hasattr(value, list_converter):
                return getattr(value, list_converter)()
            # Last resort: pass-through
            return value
                
        except Exception as e:
            logger.error("ConversionManager: Error serializing value for %s: %s", tool_name, e)
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
            # Determine callable from method or array_creator
            method_str = deserialize_config.get('method') or conversion_config.get('array_creator', '')

            # Special-case pandas dataframe/series when method lists multiple options
            # e.g., "pandas.DataFrame/pandas.Series"
            if method_str and '/' in method_str:
                exprs = [m.strip() for m in method_str.split('/') if m.strip()]
                # Choose based on input type: dict -> DataFrame, list -> Series
                if isinstance(value, dict):
                    method_str = next((m for m in exprs if m.endswith('DataFrame')), exprs[0])
                else:
                    method_str = next((m for m in exprs if m.endswith('Series')), exprs[-1])

            if not method_str:
                return value

            # Import and cache the callable
            creator = self._resolve_callable(method_str, conversion_config.get('import'))
            if creator is None:
                return value

            # If pandas: allow dict (DataFrame) and list (Series)
            if method_str.startswith('pandas.'):
                if isinstance(value, dict):
                    return creator(value)
                if isinstance(value, list):
                    return creator(value)
                return value

            # For numpy/torch paths, expect list (possibly nested)
            if isinstance(value, list):
                return creator(value)
            return value
                
        except Exception as e:
            logger.error("Error deserializing value for %s.%s: %s", tool_name, arg_name, e)
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

        converted_args: Dict[str, Any] = {}
        for arg_name, arg_value in arguments.items():
            if self.should_convert_argument(tool_name, arg_name):
                converted_args[arg_name] = self.deserialize_value(arg_value, tool_name, arg_name)
            else:
                converted_args[arg_name] = arg_value

        return converted_args

    # --- Internal helpers ---
    def _resolve_callable(self, dotted: str, optional_import_stmt: Optional[str] = None):
        """Resolve and cache a dotted callable like 'numpy.array' or 'torch.tensor'."""
        if dotted in self._callable_cache:
            return self._callable_cache[dotted]
        module_name, _, attr = dotted.partition('.')
        if not module_name or not attr:
            return None
        module = self._module_cache.get(module_name)
        try:
            if module is None:
                # Optional import hint for aliasing (e.g., 'import numpy as np') is ignored here
                module = importlib.import_module(module_name)
                self._module_cache[module_name] = module
            creator = getattr(module, attr, None)
            if creator:
                self._callable_cache[dotted] = creator
                return creator
        except Exception as e:
            logger.debug("Failed to import %s: %s", module_name, e)
        return None