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
        
        # Build tool info for LLM with enhanced formatting
        tool_info = []
        for tool in available_tools:
            tool_name = tool.get('name', 'unknown')
            description = tool.get('description', 'No description')
            
            # Get inputSchema from server if available, otherwise use parameters
            input_schema = tool.get('inputSchema', {})
            parameters = tool.get('parameters', {})
            
            param_info = []
            example_args = {}
            
            if input_schema and input_schema.get('type') == 'object':
                # Use server-provided inputSchema
                properties = input_schema.get('properties', {})
                required = input_schema.get('required', [])
                
                for param_name, param_schema in properties.items():
                    param_type = param_schema.get('type', 'string')
                    is_required = param_name in required
                    desc = param_schema.get('description', f'Parameter {param_name}')
                    
                    # Build example value based on JSON type
                    example_value = self._get_example_value_for_type(param_type)
                    example_args[param_name] = example_value
                    
                    if is_required:
                        param_info.append(f"    {param_name} ({param_type}): {desc} [required]")
                    else:
                        default = param_schema.get('default', 'None')
                        param_info.append(f"    {param_name} ({param_type}): {desc} [default: {default}]")
            else:
                # Fallback to parameters
                for param_name, param_data in parameters.items():
                    param_type = param_data.get('type', 'Any')
                    required = param_data.get('required', False)
                    desc = param_data.get('description', f'Parameter {param_name}')
                    
                    # Convert Python type to JSON type for example
                    json_type = self._convert_python_type_to_json(param_type)
                    example_value = self._get_example_value_for_type(json_type)
                    example_args[param_name] = example_value
                    
                    if required:
                        param_info.append(f"    {param_name} ({param_type}): {desc} [required]")
                    else:
                        default = param_data.get('default', 'None')
                        param_info.append(f"    {param_name} ({param_type}): {desc} [default: {default}]")
            
            # Build tool description with example arguments
            tool_desc = f"- {tool_name}: {description}"
            if param_info:
                tool_desc += f"\n  Parameters:\n" + "\n".join(param_info)
            
            if example_args:
                example_json = json.dumps(example_args, indent=2)
                tool_desc += f"\n  Example arguments: {example_json}"
            
            tool_info.append(tool_desc)
        
        # Get LLM reasoning configuration
        llm_reasoning_config = self.config.get('reasoning', {})
        system_prompt_template = llm_reasoning_config.get('system_prompt_template', 
            "You are an AI assistant that creates step-based execution plans for tools.\n\nAvailable tools:\n{tools}\n\nYour task is to create an ordered plan where each step is a tool with its arguments and reasoning.\nThe steps will be executed in sequence. Parse the query and create the execution plan.\n\nIMPORTANT RULES:\n- Tool names must match exactly from the list above\n- If required parameters are missing from the query, use placeholder values\n- Each step must include a 'why' field explaining the reasoning\n- Return a JSON object with 'plan' array and 'confidence' number")
        user_prompt_template = llm_reasoning_config.get('user_prompt_template', "User query: {query}")
        
        # Automatically generate and inject context
        context = self._generate_context(available_tools, query)
        
        # Build the complete system prompt
        base_prompt = system_prompt_template.format(tools="\n".join(tool_info))
        if context:
            system_prompt = f"{base_prompt}\n\nContext:\n{context}"
        else:
            system_prompt = base_prompt
        
        user_prompt = user_prompt_template.format(query=query)
        
        # Call LLM for reasoning only
        try:
            # Get LLM configuration
            llm_config = self.config.get('llm', {})
            model = llm_config.get('model', 'phi3:mini')
            provider = llm_config.get('provider', 'ollama')
            api_url = llm_config.get('api_url', 'http://localhost:11434/api/generate')
            timeout = llm_config.get('timeout', 30)
            options = llm_config.get('options', {'temperature': 0.0, 'top_p': 1.0})
            
            # Test if model supports JSON format
            supports_json = self._test_json_support(model, api_url)
            print(f"🔧 Model {model} JSON support: {supports_json}")
            
            # Get base JSON schema from config and enhance it with tool information
            base_schema = self.config.get('json_schema', {})
            json_schema = base_schema if supports_json else None  # Use base schema only if JSON is supported
            
            # Build the request to the LLM provider
            payload = {
                "model": model,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "options": options
            }
            
            # Use Ollama's format parameter with JSON schema
            if json_schema:
                payload["type"] = "json_schema"
                payload["options"]["json_schema"] = json_schema
                print(f"🔧 Using JSON schema enforcement with type parameter")
                print(f"🔧 Schema: {json.dumps(json_schema, indent=2)}")
            else:
                print(f"⚠️ No JSON schema available")
            
            print(f"🤖 Calling LLM ({provider}:{model}) for reasoning...")
            response = requests.post(api_url, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', '').strip()
                print(f"🤖 LLM Reasoning Response: {llm_response}")
                print(f"🔧 Raw response type: {type(llm_response)}")
                print(f"🔧 Response length: {len(llm_response)}")
                
                # Parse JSON response
                try:
                    if json_schema:
                        # With JSON Schema support, response should be properly structured
                        # But first check if it's wrapped in markdown code blocks
                        cleaned_response = self._extract_json_from_markdown(llm_response)
                        llm_json = json.loads(cleaned_response.strip())
                    else:
                        # Fallback for non-JSON responses - try to extract action information from text
                        print(f"🔧 Attempting to parse text response for action plan...")
                        llm_json = self._parse_text_response(llm_response, available_tools)
                    
                    print(f"🔧 Parsed JSON: {json.dumps(llm_json, indent=2)}")
                    
                    # Handle new step-based plan format
                    if 'plan' in llm_json:
                        # New step-based plan format
                        plan = llm_json.get('plan', [])
                        confidence = llm_json.get('confidence', 0.8)
                        
                        # Validate and clean plan steps
                        validated_plan = []
                        available_tool_names = [tool.get('name') for tool in available_tools]
                        
                        for step in plan:
                            if isinstance(step, dict):
                                tool_name = step.get('tool', '')
                                arguments = step.get('arguments', {})
                                why = step.get('why', '')
                                
                                # Validate tool name (fuzzy match if needed)
                                if tool_name in available_tool_names:
                                    validated_plan.append({
                                        'tool': tool_name,
                                        'arguments': arguments,
                                        'why': why
                                    })
                                else:
                                    # Try fuzzy matching
                                    best_match = self._find_best_tool_match(tool_name, available_tool_names)
                                    if best_match:
                                        validated_plan.append({
                                            'tool': best_match,
                                            'arguments': arguments,
                                            'why': why
                                        })
                        
                        action_plan = {
                            'plan': validated_plan,
                            'confidence': confidence
                        }
                    elif 'actions' in llm_json:
                        # Legacy actions format - convert to plan format
                        actions = llm_json.get('actions', [])
                        confidence = llm_json.get('confidence', 0.8)
                        
                        plan = []
                        for action in actions:
                            if isinstance(action, dict):
                                tool_name = action.get('tool', '')
                                arguments = action.get('arguments', {})
                                plan.append({
                                    'tool': tool_name,
                                    'arguments': arguments,
                                    'why': 'Converted from legacy format'
                                })
                        
                        action_plan = {
                            'plan': plan,
                            'confidence': confidence
                        }
                    elif 'action1' in llm_json:
                        # Legacy action1, action2, action3 format - convert to plan format
                        plan = []
                        confidence = llm_json.get('confidence', 0.8)
                        
                        # Collect all actions (action1, action2, action3, etc.)
                        for i in range(1, 4):  # Support up to 3 actions
                            action_key = f'action{i}'
                            if action_key in llm_json:
                                action_data = llm_json[action_key]
                                if isinstance(action_data, dict):
                                    tool_name = action_data.get('tool', '')
                                    arguments = action_data.get('arguments', {})
                                    
                                    if tool_name:
                                        plan.append({
                                            'tool': tool_name,
                                            'arguments': arguments,
                                            'why': f'Step {i} from legacy format'
                                        })
                        
                        action_plan = {
                            'plan': plan,
                            'confidence': confidence
                        }
                    else:
                        # Invalid format - return empty plan
                        action_plan = {
                            'plan': [],
                            'confidence': 0.0
                        }
                    print(f"✅ Action Plan: {action_plan}")
                    return action_plan
                    
                except Exception as e:
                    print(f"❌ Failed to parse LLM JSON response: {e}")
                    print(f"🤖 Raw response: {llm_response}")
                    
                    # Try to repair the JSON response
                    try:
                        cleaned_response = self._extract_json_from_markdown(llm_response)
                        if cleaned_response != llm_response:
                            print(f"🔧 Attempting to repair JSON response...")
                            llm_json = json.loads(cleaned_response.strip())
                            # Process the repaired response
                            if 'plan' in llm_json:
                                return {'plan': llm_json.get('plan', []), 'confidence': llm_json.get('confidence', 0.0)}
                    except Exception as repair_error:
                        print(f"❌ JSON repair failed: {repair_error}")
                    
                    return {'plan': [], 'confidence': 0.0, 'error': f'Failed to parse response: {e}'}
                    
            else:
                print(f"❌ LLM API error: {response.status_code}")
                return {'plan': [], 'confidence': 0.0, 'error': f'LLM API error: {response.status_code}'}
                
        except Exception as e:
            print(f"❌ Error calling LLM: {e}")
            return {'plan': [], 'confidence': 0.0, 'error': f'Error calling LLM: {e}'}
    
    def generate_json_schema(self, available_tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate JSON schema for step-based plan format.
        
        Args:
            available_tools: List of available tools with their definitions
            
        Returns:
            JSON schema for step-based plan format
        """
        if not available_tools:
            return None
        
        # Build tool-specific argument schemas
        tool_schemas = {}
        tool_enum = []
        
        for tool in available_tools:
            tool_name = tool.get('name', 'unknown')
            tool_enum.append(tool_name)
            
            # Get tool inputSchema from server if available, otherwise synthesize from parameters
            input_schema = tool.get('inputSchema', {})
            if input_schema and input_schema.get('type') == 'object':
                # Use server-provided inputSchema
                tool_schemas[tool_name] = input_schema
            else:
                # Synthesize from parameters
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
                    
                    tool_schemas[tool_name] = tool_schema
                else:
                    # For tools without parameters, allow empty object
                    tool_schemas[tool_name] = {
                        "type": "object",
                        "properties": {}
                    }
        
        # Build the main plan schema with step-based format
        schema = {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "enum": tool_enum,
                                "description": "Name of the tool to execute"
                            },
                            "arguments": {
                                "oneOf": [
                                    {
                                        "type": "object",
                                        "properties": tool_schemas.get(tool_name, {}).get("properties", {}),
                                        "required": tool_schemas.get(tool_name, {}).get("required", [])
                                    }
                                    for tool_name in tool_enum
                                ],
                                "description": "Arguments for the tool"
                            },
                            "why": {
                                "type": "string",
                                "description": "Explanation of why this step is needed"
                            }
                        },
                        "required": ["tool", "arguments", "why"],
                        "additionalProperties": False
                    },
                    "description": "Ordered list of execution steps",
                    "minItems": 1
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence level in the execution plan",
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            "required": ["plan", "confidence"],
            "additionalProperties": False
        }
        
        return schema
    
    def _build_dynamic_schema(self, available_tools):
        """Build a dynamic JSON schema based on available tools."""
        # Use the base schema from config and enhance it with tool information
        base_schema = self.config.get('json_schema', {})
        if not base_schema:
            # Fallback to a simple schema
            base_schema = {
                "type": "object",
                "properties": {
                    "action1": {
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "description": "Name of the first tool to execute"
                            },
                            "arguments": {
                                "type": "object",
                                "description": "Arguments for the first tool"
                            }
                        },
                        "required": ["tool", "arguments"]
                    },
                    "action2": {
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "description": "Name of the second tool to execute"
                            },
                            "arguments": {
                                "type": "object",
                                "description": "Arguments for the second tool"
                            }
                        },
                        "required": ["tool", "arguments"]
                    },
                    "action3": {
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "description": "Name of the third tool to execute"
                            },
                            "arguments": {
                                "type": "object",
                                "description": "Arguments for the third tool"
                            }
                        },
                        "required": ["tool", "arguments"]
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Explanation of the action plan choices"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence level in the action plan",
                        "minimum": 0.0,
                        "maximum": 1.0
                    }
                },
                "required": ["action1", "reasoning", "confidence"]
            }
        
        # Enhance the schema with tool-specific information
        if available_tools:
            schema = base_schema.copy()
            
            # Get tool names for enum
            tool_names = [tool.get('name', 'unknown') for tool in available_tools]
            
            # Build tool-specific argument schemas
            arguments_schema = {}
            for tool in available_tools:
                tool_name = tool.get('name', 'unknown')
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
                else:
                    # For tools without parameters, allow empty object
                    arguments_schema[tool_name] = {
                        "type": "object",
                        "properties": {}
                    }
            
            # Update the schema with tool-specific information for each action
            for i in range(1, 4):  # action1, action2, action3
                action_key = f'action{i}'
                if action_key in schema['properties']:
                    action_schema = schema['properties'][action_key]
                    if 'properties' in action_schema:
                        # Update tool enum
                        if 'tool' in action_schema['properties']:
                            action_schema['properties']['tool']['enum'] = tool_names
                        
                        # Update arguments schema
                        if 'arguments' in action_schema['properties']:
                            action_schema['properties']['arguments']['properties'] = arguments_schema
            
            return schema
        
        return base_schema
    
    def _get_example_value_for_type(self, json_type: str) -> Any:
        """Get example value for a JSON schema type.
        
        Args:
            json_type: JSON schema type (string, integer, number, boolean, array, object)
            
        Returns:
            Example value for the type
        """
        if json_type == 'integer':
            return 1
        elif json_type == 'number':
            return 1.0
        elif json_type == 'boolean':
            return True
        elif json_type == 'array':
            return []
        elif json_type == 'object':
            return {}
        else:  # string or unknown
            return "example"

    def _find_best_tool_match(self, tool_name: str, available_tool_names: List[str], threshold: float = 0.6) -> Optional[str]:
        """Find the best matching tool name using fuzzy matching.
        
        Args:
            tool_name: Tool name from LLM response
            available_tool_names: List of available tool names
            threshold: Minimum similarity threshold (0.0 to 1.0)
            
        Returns:
            Best matching tool name or None if no match above threshold
        """
        if not tool_name or not available_tool_names:
            return None
        
        # Exact match first
        if tool_name in available_tool_names:
            return tool_name
        
        # Try partial matches
        for available_name in available_tool_names:
            if tool_name.lower() in available_name.lower() or available_name.lower() in tool_name.lower():
                return available_name
        
        # Try fuzzy matching using simple string similarity
        best_match = None
        best_score = 0.0
        
        for available_name in available_tool_names:
            # Simple similarity calculation
            shorter = min(tool_name, available_name)
            longer = max(tool_name, available_name)
            
            if len(longer) == 0:
                score = 1.0
            else:
                # Calculate similarity based on common characters
                common_chars = sum(1 for c in shorter if c in longer)
                score = common_chars / len(longer)
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = available_name
        
        return best_match

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

    def _generate_context(self, available_tools: List[Dict[str, Any]], query: str = None) -> str:
        """Automatically generate context using the prompt generator if available.
        
        Args:
            available_tools: List of available tools
            query: User query to analyze
            
        Returns:
            Context string about tool relationships and usage patterns
        """
        try:
            # Import and call the prompt generator directly
            from .prompt_generator import generate_context
            
            # Try to find server config automatically
            server_config_path = self._find_server_config()
            
            if server_config_path:
                # Call the prompt generator
                context = generate_context(available_tools, str(server_config_path))
                if context:
                    print(f"🔧 Injected context from prompt generator")
                return context
            else:
                return ""
                
        except Exception as e:
            # Silently fail - context injection is optional
            return ""
    
    def _find_server_config(self) -> str:
        """Try to find the server config file automatically."""
        try:
            # Look for server config in common locations
            possible_paths = [
                # Relative to reasoning config
                self.config_path.parent.parent / "examples" / "explodata" / "server_config.yaml",
                # In examples directory
                Path("examples") / "explodata" / "server_config.yaml",
                # In current directory
                Path("server_config.yaml"),
            ]
            
            for path in possible_paths:
                if path.exists():
                    return str(path)
            
            return ""
        except Exception:
            return ""

    def _test_json_support(self, model: str, api_url: str) -> bool:
        """Test if the model supports JSON format enforcement."""
        try:
            # Simple test with JSON schema
            simple_schema = {
                "type": "object",
                "properties": {
                    "test": {"type": "string"}
                },
                "required": ["test"]
            }
            
            test_payload = {
                "model": model,
                "prompt": "Respond with a simple JSON: {\"test\": \"hello\"}",
                "stream": False,
                "type": "json_schema",
                "options": {"json_schema": simple_schema}
            }
            
            response = requests.post(api_url, json=test_payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', '').strip()
                
                # Check if response is valid JSON
                try:
                    json.loads(llm_response)
                    return True
                except:
                    return False
            else:
                return False
        except Exception as e:
            print(f"🔧 JSON support test failed: {e}")
            return False

    def _parse_text_response(self, text_response: str, available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse text response to extract action plan information."""
        try:
            # Get tool names for pattern matching
            tool_names = [tool.get('name', '') for tool in available_tools]
            
            # Look for patterns like "np_mean", "np_std", etc.
            actions = []
            lines = text_response.lower().split('\n')
            
            for line in lines:
                for tool_name in tool_names:
                    if tool_name in line:
                        # Try to extract arguments from the line
                        arguments = self._extract_arguments_from_text(line, tool_name)
                        
                        actions.append({
                            'tool': tool_name,
                            'arguments': arguments
                        })
                        break  # Found one tool, move to next line
            
            # If we found actions, create a MyActionPlan format
            if actions:
                return {
                    'MyActionPlan': actions,
                    'reasoning': text_response,
                    'confidence': 0.8
                }
            else:
                # No actions found, return empty plan
                return {
                    'actions': [],
                    'reasoning': text_response,
                    'confidence': 0.0
                }
                
        except Exception as e:
            print(f"🔧 Text parsing failed: {e}")
            return {
                'actions': [],
                'reasoning': text_response,
                'confidence': 0.0
            }
    
    def _extract_arguments_from_text(self, text: str, tool_name: str) -> Dict[str, Any]:
        """Extract arguments for a specific tool from text."""
        arguments = {}
        
        # Look for array patterns like [1, 2, 3, 4, 5]
        import re
        array_pattern = r'\[([^\]]+)\]'
        arrays = re.findall(array_pattern, text)
        
        if arrays:
            try:
                # Convert the first array found to actual array
                import ast
                array_str = '[' + arrays[0] + ']'
                arguments['a'] = ast.literal_eval(array_str)
            except:
                # If parsing fails, keep as string
                arguments['a'] = arrays[0]
        
        return arguments
    
    def _extract_json_from_markdown(self, text: str) -> str:
        """Extract JSON content from markdown code blocks."""
        import re
        
        # Look for ```json...``` or ```...``` blocks
        json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        if matches:
            # Return the first JSON block found
            return matches[0].strip()
        else:
            # No markdown blocks found, return original text
            return text.strip()


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