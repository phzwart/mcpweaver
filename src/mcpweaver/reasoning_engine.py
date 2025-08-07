"""
Pure LLM-based reasoning engine for tool selection and argument extraction.

This engine:
1. Loads behavior configuration from YAML
2. Uses configured prompts and instructions
3. Generates JSON schemas from tool definitions
4. Performs pure reasoning without execution
5. All behavior is configurable via YAML
"""

import yaml
import json
import requests
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


class ReasoningEngine:
    """Pure LLM-based reasoning engine for tool selection and argument extraction."""
    
    def __init__(self, config_path: str):
        """Initialize the reasoning engine.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def reason_about_query(self, query: str, available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Main reasoning method - pure function with no side effects.
        
        Args:
            query: User's natural language query
            available_tools: List of available tools with their definitions
            
        Returns:
            Execution plan with tools, arguments, reasoning, and confidence
        """
        print(f"🧠 Reasoning about query: {query}")
        
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
        
        # Get LLM reasoning configuration
        llm_reasoning_config = self.config.get('reasoning', {})
        system_prompt_template = llm_reasoning_config.get('system_prompt_template', 
            "You are an AI assistant that selects appropriate tools for user queries.\n\nAvailable tools:\n{tools}\n\nYour task is to select appropriate tools and extract arguments.")
        user_prompt_template = llm_reasoning_config.get('user_prompt_template', "User query: {query}")
        
        # Format the system prompt with available tools
        system_prompt = system_prompt_template.format(tools="\n".join(tool_info))
        user_prompt = user_prompt_template.format(query=query)
        
        # Call LLM for reasoning only
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
            
            print(f"🤖 Calling LLM ({provider}:{model}) for reasoning...")
            response = requests.post(api_url, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', '').strip()
                print(f"🤖 LLM Reasoning Response: {llm_response}")
                
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
                        'confidence': confidence
                    }
                    
                    print(f"✅ Action Plan: {action_plan}")
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
    
    def generate_json_schema(self, available_tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate JSON schema for structured LLM responses.
        
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
                    "description": "Arguments for each tool"
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
                        "description": param_data.get('description', f'Parameter {param_name}')
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
    
    def _call_llm(self, prompt: str, schema: Dict = None) -> str:
        """Private method to call LLM with structured output.
        
        Args:
            prompt: The prompt to send to the LLM
            schema: Optional JSON schema for structured output
            
        Returns:
            LLM response as string
        """
        llm_config = self.config.get('llm', {})
        model = llm_config.get('model', 'phi3:mini')
        provider = llm_config.get('provider', 'ollama')
        api_url = llm_config.get('api_url', 'http://localhost:11434/api/generate')
        timeout = llm_config.get('timeout', 30)
        options = llm_config.get('options', {'temperature': 0.1, 'top_p': 0.9})
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options
        }
        
        if schema:
            payload["format"] = "json"
            payload["options"]["json_schema"] = schema
        
        response = requests.post(api_url, json=payload, timeout=timeout)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        else:
            raise Exception(f"LLM API error: {response.status_code}")
    
    def _parse_llm_response(self, response: str, schema: Dict = None) -> Dict[str, Any]:
        """Private method to parse LLM response into structured format.
        
        Args:
            response: Raw LLM response
            schema: Optional JSON schema used for generation
            
        Returns:
            Parsed response as dictionary
        """
        try:
            if schema:
                # Direct JSON parsing (Ollama guarantees valid JSON with schema)
                return json.loads(response.strip())
            else:
                # Fallback to regex extraction for non-schema responses
                try:
                    return json.loads(response.strip())
                except json.JSONDecodeError:
                    llm_reasoning_config = self.config.get('reasoning', {})
                    json_extraction_regex = llm_reasoning_config.get('json_extraction_regex', r'\{.*\}')
                    json_match = re.search(json_extraction_regex, response, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                    else:
                        raise Exception("Could not extract JSON from response")
        except Exception as e:
            raise Exception(f"Failed to parse LLM response: {e}")


def main():
    """Main function for testing."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python reasoning_engine.py <config.yaml> [query]")
        print("Example: python reasoning_engine.py reasoning_config.yaml 'Calculate the mean of [1,2,3,4,5]'")
        return
    
    config_path = sys.argv[1]
    query = sys.argv[2] if len(sys.argv) > 2 else "Calculate the mean of [1,2,3,4,5]"
    
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
    
    try:
        engine = ReasoningEngine(config_path)
        plan = engine.reason_about_query(query, available_tools)
        print("\n" + "="*50)
        print("🧠 Reasoning Engine Response:")
        print("="*50)
        print(json.dumps(plan, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 