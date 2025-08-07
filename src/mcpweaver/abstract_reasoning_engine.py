"""
Abstract Reasoning Engine for symbolic tool selection and argument extraction.

This engine:
1. Supports abstract reasoning with symbolic references
2. Allows reasoning about data structures without concrete values
3. Uses placeholders like <numpy array named A> for abstract reasoning
4. Generates execution plans with symbolic arguments
5. All behavior is configurable via YAML
"""

import yaml
import json
import requests
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


class AbstractReasoningEngine:
    """Abstract LLM-based reasoning engine for symbolic tool selection and argument extraction."""
    
    def __init__(self, config_path: str):
        """Initialize the abstract reasoning engine.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def reason_about_query(self, query: str, available_tools: List[Dict[str, Any]], 
                          symbolic_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main abstract reasoning method - pure function with no side effects.
        
        Args:
            query: User's natural language query (can contain symbolic references)
            available_tools: List of available tools with their definitions
            symbolic_data: Optional mapping of symbolic names to data descriptions
            
        Returns:
            Execution plan with tools, symbolic arguments, reasoning, and confidence
        """
        print(f"🧠 Abstract reasoning about query: {query}")
        
        # Build tool info for LLM
        tool_info = []
        for tool in available_tools:
            tool_name = tool.get('name', 'unknown')
            description = tool.get('description', 'No description')
            parameters = tool.get('parameters', {})
            
            param_info = []
            for param_name, param_data in parameters.items():
                param_type = param_data.get('type', 'Any')
                required = param_data.get('required', False)
                desc = param_data.get('description', f'Parameter {param_name}')
                
                if required:
                    param_info.append(f"    {param_name} ({param_type}): {desc} [required]")
                else:
                    default = param_data.get('default', 'None')
                    param_info.append(f"    {param_name} ({param_type}): {desc} [default: {default}]")
            
            if param_info:
                tool_info.append(f"- {tool_name}: {description}\n  Parameters:\n" + "\n".join(param_info))
            else:
                tool_info.append(f"- {tool_name}: {description}")
        
        # Add symbolic data context if provided
        symbolic_context = ""
        if symbolic_data:
            symbolic_context = "\n\nSymbolic Data Context:\n"
            for name, description in symbolic_data.items():
                symbolic_context += f"- {name}: {description}\n"
        
        # Get LLM reasoning configuration
        llm_reasoning_config = self.config.get('reasoning', {})
        system_prompt_template = llm_reasoning_config.get('system_prompt_template', 
            "You are an AI assistant that selects appropriate tools for user queries.\n\nAvailable tools:\n{tools}\n\nYour task is to select appropriate tools and extract arguments. You can use symbolic references like <numpy array named A> in your reasoning.")
        user_prompt_template = llm_reasoning_config.get('user_prompt_template', "User query: {query}")
        
        # Format the system prompt with available tools and symbolic context
        system_prompt = system_prompt_template.format(tools="\n".join(tool_info)) + symbolic_context
        user_prompt = user_prompt_template.format(query=query)
        
        # Call LLM for abstract reasoning only
        try:
            # Get LLM configuration
            llm_config = self.config.get('llm', {})
            model = llm_config.get('model', 'phi3:mini')
            provider = llm_config.get('provider', 'ollama')
            api_url = llm_config.get('api_url', 'http://localhost:11434/api/generate')
            timeout = llm_config.get('timeout', 30)
            options = llm_config.get('options', {'temperature': 0.1, 'top_p': 0.9})
            
            # Generate JSON schema from available tools
            json_schema = self.generate_json_schema(available_tools)
            
            # Build the request to the LLM provider
            payload = {
                "model": model,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "options": options
            }
            
            # Add JSON schema if available (Ollama native support)
            if json_schema:
                payload["format"] = "json"
                payload["options"]["json_schema"] = json_schema
            
            print(f"🤖 Calling LLM ({provider}:{model}) for abstract reasoning...")
            response = requests.post(api_url, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', '').strip()
                print(f"🤖 LLM Abstract Reasoning Response: {llm_response}")
                
                # Parse JSON response
                try:
                    # With Ollama's native JSON Schema support, response should be properly structured
                    if json_schema:
                        # Direct JSON parsing (Ollama guarantees valid JSON)
                        llm_json = json.loads(llm_response.strip())
                    else:
                        # Fallback to regex extraction for non-schema responses
                        try:
                            llm_json = json.loads(llm_response.strip())
                        except json.JSONDecodeError:
                            json_extraction_regex = llm_reasoning_config.get('json_extraction_regex', r'\{.*\}')
                            json_match = re.search(json_extraction_regex, llm_response, re.DOTALL)
                            if json_match:
                                llm_json = json.loads(json_match.group())
                            else:
                                print(f"❌ Could not extract JSON from response")
                                print(f"🤖 Raw response: {llm_response}")
                                return {'tools': [], 'arguments': {}, 'reasoning': '', 'confidence': 0.0, 'error': 'Could not parse LLM response'}
                    
                    selected_tools = llm_json.get('tools', [])
                    arguments = llm_json.get('arguments', {})
                    reasoning = llm_json.get('reasoning', '')
                    confidence = llm_json.get('confidence', 0.8)
                    
                    action_plan = {
                        'tools': selected_tools,
                        'arguments': arguments,
                        'reasoning': reasoning,
                        'confidence': confidence,
                        'symbolic_references': self._extract_symbolic_references(arguments)
                    }
                    
                    print(f"✅ Abstract Action Plan: {action_plan}")
                    return action_plan
                    
                except Exception as e:
                    print(f"❌ Failed to parse LLM JSON response: {e}")
                    print(f"🤖 Raw response: {llm_response}")
                    return {'tools': [], 'arguments': {}, 'reasoning': '', 'confidence': 0.0, 'error': f'Failed to parse response: {e}'}
                    
            else:
                print(f"❌ LLM API error: {response.status_code}")
                return {'tools': [], 'arguments': {}, 'reasoning': '', 'confidence': 0.0, 'error': f'LLM API error: {response.status_code}'}
                
        except Exception as e:
            print(f"❌ Error calling LLM: {e}")
            return {'tools': [], 'arguments': {}, 'reasoning': '', 'confidence': 0.0, 'error': f'Error calling LLM: {e}'}
    
    def _extract_symbolic_references(self, arguments: Dict[str, Any]) -> List[str]:
        """Extract symbolic references from arguments.
        
        Args:
            arguments: The arguments dictionary
            
        Returns:
            List of symbolic references found in arguments
        """
        symbolic_refs = []
        
        def find_symbolic_refs(obj):
            if isinstance(obj, str):
                # Look for patterns like <numpy array named A> or <variable X>
                matches = re.findall(r'<[^>]+>', obj)
                symbolic_refs.extend(matches)
            elif isinstance(obj, dict):
                for value in obj.values():
                    find_symbolic_refs(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_symbolic_refs(item)
        
        find_symbolic_refs(arguments)
        return list(set(symbolic_refs))  # Remove duplicates
    
    def generate_json_schema(self, available_tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate JSON schema for structured LLM responses with symbolic support.
        
        Args:
            available_tools: List of available tools with their definitions
            
        Returns:
            JSON schema for structured LLM responses
        """
        if not available_tools:
            return None
        
        # Build schema based on available tools
        schema = {
            "type": "object",
            "properties": {
                "tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tool names to use"
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments for each tool (can contain symbolic references like <numpy array named A>)"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explanation of reasoning"
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence level (0.0 to 1.0)",
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            "required": ["tools", "arguments"]
        }
        
        # Add tool-specific argument schemas
        arguments_schema = {}
        tool_enum = []
        
        for tool in available_tools:
            tool_name = tool.get('name', 'unknown')
            tool_enum.append(tool_name)
            
            # Get tool parameters
            parameters = tool.get('parameters', {})
            if parameters:
                tool_schema = {
                    "type": "object",
                    "properties": {}
                }
                
                for param_name, param_data in parameters.items():
                    param_type = param_data.get('type', 'Any')
                    json_type = self._convert_python_type_to_json(param_type)
                    
                    tool_schema["properties"][param_name] = {
                        "type": json_type,
                        "description": param_data.get('description', f'Parameter {param_name} (can be symbolic reference)')
                    }
                    
                    # Add required field if parameter is required
                    if param_data.get('required', False):
                        if 'required' not in tool_schema:
                            tool_schema['required'] = []
                        tool_schema['required'].append(param_name)
                
                arguments_schema[tool_name] = tool_schema
        
        # Update the main schema
        schema["properties"]["tools"]["items"]["enum"] = tool_enum
        schema["properties"]["arguments"]["properties"] = arguments_schema
        
        return schema
    
    def _convert_python_type_to_json(self, python_type: str) -> str:
        """Convert Python type to JSON schema type."""
        type_mapping = {
            'string': 'string',
            'str': 'string',
            'integer': 'integer',
            'int': 'integer',
            'number': 'number',
            'float': 'number',
            'boolean': 'boolean',
            'bool': 'boolean',
            'array': 'array',
            'list': 'array',
            'object': 'object',
            'dict': 'object',
            'Any': 'string'  # Default to string for unknown types
        }
        
        return type_mapping.get(python_type.lower(), 'string')
    
    def create_symbolic_data_mapping(self, data_structures: Dict[str, Any]) -> Dict[str, str]:
        """Create a mapping of symbolic names to data descriptions.
        
        Args:
            data_structures: Dictionary of data structures with their descriptions
            
        Returns:
            Mapping of symbolic names to descriptions
        """
        symbolic_mapping = {}
        
        for name, description in data_structures.items():
            if isinstance(description, dict):
                # Handle structured data descriptions
                data_type = description.get('type', 'unknown')
                shape = description.get('shape', '')
                dtype = description.get('dtype', '')
                
                if data_type == 'numpy_array':
                    symbolic_mapping[f"<numpy array named {name}>"] = f"numpy array {name} with shape {shape}, dtype {dtype}"
                elif data_type == 'pandas_dataframe':
                    symbolic_mapping[f"<dataframe named {name}>"] = f"pandas dataframe {name} with shape {shape}"
                elif data_type == 'list':
                    symbolic_mapping[f"<list named {name}>"] = f"list {name} with {description.get('length', 'unknown')} elements"
                else:
                    symbolic_mapping[f"<{data_type} named {name}>"] = f"{data_type} {name}"
            else:
                # Handle simple string descriptions
                symbolic_mapping[f"<variable named {name}>"] = str(description)
        
        return symbolic_mapping


def main():
    """Main function for testing abstract reasoning."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python abstract_reasoning_engine.py <config.yaml> [query]")
        print("Example: python abstract_reasoning_engine.py reasoning_config.yaml 'Compute the mean of <numpy array named A>'")
        return
    
    config_path = sys.argv[1]
    query = sys.argv[2] if len(sys.argv) > 2 else "Compute the mean of <numpy array named A>"
    
    # Mock available tools for testing
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
    
    # Create symbolic data mapping
    symbolic_data = {
        "A": {
            "type": "numpy_array",
            "shape": "(100, 3)",
            "dtype": "float64"
        },
        "B": {
            "type": "numpy_array", 
            "shape": "(50, 2)",
            "dtype": "int32"
        }
    }
    
    try:
        engine = AbstractReasoningEngine(config_path)
        symbolic_mapping = engine.create_symbolic_data_mapping(symbolic_data)
        
        plan = engine.reason_about_query(query, available_tools, symbolic_mapping)
        print("\n" + "="*50)
        print("🧠 Abstract Reasoning Engine Response:")
        print("="*50)
        print(json.dumps(plan, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 