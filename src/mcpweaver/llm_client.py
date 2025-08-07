"""
Generic LLM Client that uses YAML configuration for behavior and prompt instructions.

This client:
1. Loads behavior configuration from YAML
2. Connects to MCP server for tools
3. Uses configured prompts and instructions
4. Manages tool usage based on guidelines
5. All behavior is configurable via YAML
"""

import yaml
import asyncio
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from .conversion_manager import ConversionManager

class LLMClient:
    """LLM client that can interact with MCP servers."""
    
    def __init__(self, config_path: str):
        """Initialize the LLM client.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Initialize conversion manager
        serialization_config = self.config.get('serialization', {})
        conversions_file = serialization_config.get('conversions_file')
        if conversions_file:
            # Resolve relative path from config file location
            config_dir = self.config_path.parent
            conversions_path = config_dir / conversions_file
            self.conversion_manager = ConversionManager(str(conversions_path))
        else:
            # Use default conversions file from the package
            self.conversion_manager = ConversionManager()
        
        # MCP server configuration
        mcp_config = self.config.get('mcp_server', {})
        self.mcp_server_url = f"http://{mcp_config.get('host', 'localhost')}:{mcp_config.get('port', 8080)}"
        self.timeout = mcp_config.get('timeout', 10)
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get_system_prompt(self) -> str:
        """Get the system prompt from configuration."""
        return self.config['prompts']['system_prompt']
    
    def get_user_prompt(self, query: str) -> str:
        """Get the user prompt template filled with the query."""
        template = self.config['prompts']['user_prompt_template']
        return template.format(query=query)
    
    def get_tool_guidelines(self) -> Dict[str, str]:
        """Get tool usage guidelines."""
        return self.config.get('tools', {})
    
    def get_behavior_instructions(self) -> str:
        """Get behavior instructions."""
        return self.config['behavior']['instructions']
    
    def _convert_arguments_for_arrays(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert arguments to appropriate types based on conversion configuration."""
        return self.conversion_manager.convert_arguments(tool_name, arguments)

    def reason_about_query(self, query: str, available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Pure reasoning - returns action plan, doesn't execute anything!
        
        Args:
            query: User's natural language query
            available_tools: List of available tools from MCP server
            
        Returns:
            Action plan with tools and arguments to execute
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
        llm_reasoning_config = self.config.get('llm_reasoning', {})
        system_prompt_template = llm_reasoning_config.get('system_prompt_template', 
            "You are an AI assistant that helps users with operations.\n\nAvailable tools:\n{tools}\n\nYour task is to select appropriate tools and extract arguments.")
        user_prompt_template = llm_reasoning_config.get('user_prompt_template', "User query: {query}\n\nRespond with JSON only:")
        
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
            
            # Try to generate schema from server first, fallback to config
            json_schema = self.generate_json_schema_from_server()
            if not json_schema:
                # Fallback to config schema if available
                json_schema = llm_config.get('json_schema')
            
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
                            import re
                            json_extraction_regex = llm_reasoning_config.get('json_extraction_regex', r'\{.*\}')
                            json_match = re.search(json_extraction_regex, llm_response, re.DOTALL)
                            if json_match:
                                llm_json = json.loads(json_match.group())
                            else:
                                print(f"❌ Could not extract JSON from response")
                                print(f"🤖 Raw response: {llm_response}")
                                return {'tools': [], 'arguments': {}, 'error': 'Could not parse LLM response'}
                    
                    selected_tools = llm_json.get('tools', [])
                    arguments = llm_json.get('arguments', {})
                    reasoning = llm_json.get('reasoning', '')
                    
                    action_plan = {
                        'tools': selected_tools,
                        'arguments': arguments,
                        'reasoning': reasoning
                    }
                    
                    print(f"✅ Action Plan: {action_plan}")
                    return action_plan
                    
                except Exception as e:
                    print(f"❌ Failed to parse LLM JSON response: {e}")
                    print(f"🤖 Raw response: {llm_response}")
                    return {'tools': [], 'arguments': {}, 'error': f'Failed to parse response: {e}'}
                    
            else:
                print(f"❌ LLM API error: {response.status_code}")
                return {'tools': [], 'arguments': {}, 'error': f'LLM API error: {response.status_code}'}
                
        except Exception as e:
            print(f"❌ Error calling LLM: {e}")
            return {'tools': [], 'arguments': {}, 'error': f'Error calling LLM: {e}'}

    def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call a tool through the MCP server."""
        if arguments is None:
            arguments = {}
        
        # Don't convert arguments on the client side - let the server handle conversion
        print(f"🔧 Client: Sending arguments: {arguments}")
        
        try:
            response = requests.post(
                self.mcp_server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    return result["result"]
                else:
                    raise Exception(f"Tool call failed: {result.get('error', 'Unknown error')}")
            else:
                raise Exception(f"HTTP error: {response.status_code}")
                
        except Exception as e:
            raise Exception(f"Error calling tool {tool_name}: {e}")
    

    
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
    
    def build_tool_sequence(self, query: str) -> List[str]:
        """Let the LLM decide which tools to use based on the query."""
        # TODO: Implement LLM-based tool selection
        # For now, return empty sequence
        return []
    
    def extract_arguments_from_results(self, tool_name: str, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract arguments for a tool from previous tool results."""
        # Get argument extraction rules from config
        argument_rules = self.config.get('argument_extraction', {})
        tool_rules = argument_rules.get(tool_name, {})
        
        if not tool_rules:
            return {}
        
        arguments = {}
        
        for arg_name, extraction_rule in tool_rules.items():
            if isinstance(extraction_rule, dict):
                # Complex extraction rule
                source_tool = extraction_rule.get('from_tool')
                source_field = extraction_rule.get('field')
                extraction_type = extraction_rule.get('type', 'direct')
                
                if source_tool in previous_results:
                    source_data = previous_results[source_tool]
                    
                    if extraction_type == 'random':
                        # Extract random item from list
                        if isinstance(source_data, list) and len(source_data) > 0:
                            import random
                            random_item = random.choice(source_data)
                            if source_field:
                                arguments[arg_name] = random_item.get(source_field, '')
                            else:
                                arguments[arg_name] = random_item
                        elif isinstance(source_data, dict) and 'files' in source_data:
                            # Handle case where source_data is a dict with 'files' field
                            files_list = source_data['files']
                            if isinstance(files_list, list) and len(files_list) > 0:
                                import random
                                random_item = random.choice(files_list)
                                if source_field:
                                    arguments[arg_name] = random_item.get(source_field, '')
                                else:
                                    arguments[arg_name] = random_item
                    elif extraction_type == 'first':
                        # Extract first item from list
                        if isinstance(source_data, list) and len(source_data) > 0:
                            first_item = source_data[0]
                            if source_field:
                                arguments[arg_name] = first_item.get(source_field, '')
                            else:
                                arguments[arg_name] = first_item
                        elif isinstance(source_data, dict) and 'files' in source_data:
                            # Handle case where source_data is a dict with 'files' field
                            files_list = source_data['files']
                            if isinstance(files_list, list) and len(files_list) > 0:
                                first_item = files_list[0]
                                if source_field:
                                    arguments[arg_name] = first_item.get(source_field, '')
                                else:
                                    arguments[arg_name] = first_item
                    elif extraction_type == 'direct':
                        # Use the data directly
                        if source_field and isinstance(source_data, dict):
                            arguments[arg_name] = source_data.get(source_field, '')
                        else:
                            arguments[arg_name] = source_data
        
        return arguments
    
    def execute_sequence(self, sequence: List[str]) -> Dict[str, Any]:
        """Execute a sequence of tools and return results."""
        results = {}
        
        for tool_name in sequence:
            try:
                print(f"🔧 Executing: {tool_name}")
                
                # Extract arguments from previous results
                arguments = self.extract_arguments_from_results(tool_name, results)
                if arguments:
                    print(f"📝 Using arguments: {arguments}")
                
                result = self.call_mcp_tool(tool_name, arguments)
                results[tool_name] = result
                print(f"✅ {tool_name}: {result}")
            except Exception as e:
                results[tool_name] = f"ERROR: {e}"
                print(f"❌ {tool_name}: {e}")
        
        return results
    
    def execute_sequence_with_arguments(self, sequence: List[str], arguments: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a sequence of tools with specific arguments."""
        results = {}
        
        for tool_name in sequence:
            try:
                print(f"🔧 Executing: {tool_name}")
                
                # Get arguments for this tool
                tool_args = arguments.get(tool_name, {})
                
                # Replace USE_OUTPUT_FROM_ placeholders with actual results
                if tool_args:
                    for arg_name, arg_value in tool_args.items():
                        if isinstance(arg_value, str) and arg_value.startswith("USE_OUTPUT_FROM_"):
                            source_tool = arg_value.replace("USE_OUTPUT_FROM_", "")
                            if source_tool in results:
                                # Check if the previous tool failed
                                previous_result = results[source_tool]
                                if isinstance(previous_result, str) and previous_result.startswith("ERROR:"):
                                    print(f"❌ Skipping {tool_name} because {source_tool} failed: {previous_result}")
                                    results[tool_name] = f"ERROR: Skipped due to failure of {source_tool}"
                                    break
                                tool_args[arg_name] = previous_result
                
                # Extract arguments from previous results if needed
                if not tool_args:
                    tool_args = self.extract_arguments_from_results(tool_name, results)
                
                if tool_args:
                    print(f"📝 Using arguments: {tool_args}")
                
                result = self.call_mcp_tool(tool_name, tool_args)
                results[tool_name] = result
                print(f"✅ {tool_name}: {result}")
                
            except Exception as e:
                results[tool_name] = f"ERROR: {e}"
                print(f"❌ {tool_name}: {e}")
        
        return results
    
    def extract_arguments_from_query(self, query: str, selected_tools: List[str], tool_selection: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Let the LLM extract arguments from the query."""
        # TODO: Implement LLM-based argument extraction
        # For now, return empty arguments
        return {}
    
    def get_tool_parameters_from_server(self, tool_name: str) -> List[str]:
        """Get parameter information for a tool from the server."""
        try:
            # Get tool info from server
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
                if "result" in result and "parameters" in result["result"]:
                    parameters = result["result"]["parameters"]
                    param_info = []
                    for param_name, param_data in parameters.items():
                        desc = param_data.get('description', f'Parameter {param_name}')
                        param_type = param_data.get('type', 'Any')
                        required = param_data.get('required', False)
                        
                        if required:
                            param_info.append(f"    {param_name} ({param_type}): {desc} [required]")
                        else:
                            default = param_data.get('default', 'None')
                            param_info.append(f"    {param_name} ({param_type}): {desc} [default: {default}]")
                    
                    return param_info
            
            return []
            
        except Exception as e:
            print(f"⚠️  Could not get parameters for {tool_name}: {e}")
            return []

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
                if "result" in result:
                    return result["result"]
            
            return None
            
        except Exception as e:
            print(f"⚠️  Could not get tool info for {tool_name}: {e}")
            return None

    def generate_json_schema_from_server(self) -> Optional[Dict[str, Any]]:
        """Generate JSON schema from available tools on the server."""
        try:
            server_tools = self.get_available_tools()
            
            if not server_tools:
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
                    }
                },
                "required": ["tools", "arguments"]
            }
            
            # Add tool-specific argument schemas
            arguments_schema = {}
            tool_enum = []
            
            for tool in server_tools:
                tool_name = tool.get('name', 'unknown')
                tool_enum.append(tool_name)
                
                # Get tool parameters
                param_info = self.get_tool_parameters_from_server(tool_name)
                if param_info:
                    tool_schema = {
                        "type": "object",
                        "properties": {}
                    }
                    
                    for param_line in param_info:
                        # Parse parameter line like "    file_path (string): File path [required]"
                        if param_line.strip().startswith("    "):
                            param_parts = param_line.strip().split(" (")
                            if len(param_parts) >= 2:
                                param_name = param_parts[0]
                                type_part = param_parts[1].split(")")[0]
                                
                                # Map Python types to JSON types
                                json_type = self._convert_python_type_to_json(type_part)
                                
                                tool_schema["properties"][param_name] = {
                                    "type": json_type,
                                    "description": param_line.split(": ")[-1].split(" [")[0] if ": " in param_line else ""
                                }
                    
                    arguments_schema[tool_name] = tool_schema
            
            # Update the main schema
            schema["properties"]["tools"]["items"]["enum"] = tool_enum
            schema["properties"]["arguments"]["properties"] = arguments_schema
            
            return schema
            
        except Exception as e:
            print(f"⚠️  Could not generate schema from server: {e}")
            return None

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
    
    def generate_response(self, query: str, tool_results: Dict[str, Any]) -> str:
        """Generate a response based on tool results and configuration."""
        response_format = self.config.get('response_format', {})
        response_templates = self.config.get('response_templates', {})
        
        response_parts = []
        
        # Include reasoning if configured
        if response_format.get('explain_reasoning', False):
            reasoning_header = response_templates.get('reasoning_header', "🤔 **My Reasoning:**")
            response_parts.append(reasoning_header)
            response_parts.append("I used the following tools to answer your query:")
            for tool_name in tool_results.keys():
                response_parts.append(f"- {tool_name}")
            response_parts.append("")
        
        # Include tool calls if configured
        if response_format.get('include_tool_calls', False):
            tool_results_header = response_templates.get('tool_results_header', "🔧 **Tool Results:**")
            response_parts.append(tool_results_header)
            for tool_name, result in tool_results.items():
                response_parts.append(f"**{tool_name}:** {result}")
            response_parts.append("")
        
        # Provide summary
        if response_format.get('provide_summary', False):
            summary_header = response_templates.get('summary_header', "📊 **Summary:**")
            response_parts.append(summary_header)
            # Use configurable summary logic
            summary_logic = self.config.get('summary_logic', {})
            for tool_name, summary_config in summary_logic.items():
                if tool_name in tool_results:
                    result = tool_results[tool_name]
                    # Simple success condition check
                    success = bool(result) if result != "ERROR: " else False
                    if success:
                        response_parts.append(summary_config.get('success_message', f"✅ {tool_name} completed successfully"))
                    else:
                        response_parts.append(summary_config.get('failure_message', f"❌ {tool_name} failed"))
            response_parts.append("")
        
        # Suggest next steps
        if response_format.get('suggest_next_steps', False):
            next_steps_header = response_templates.get('next_steps_header', "💡 **Next Steps:**")
            response_parts.append(next_steps_header)
            next_steps = self.config.get('next_steps', [])
            for step in next_steps:
                response_parts.append(f"- {step}")
        
        return "\n".join(response_parts)
    
    def generate_tools_info_response(self) -> str:
        """Generate a response listing available tools from server."""
        response_templates = self.config.get('response_templates', {})
        tools_info_header = response_templates.get('tools_info_header', "🛠️ **Available Tools:**")
        next_steps_header = response_templates.get('next_steps_header', "💡 **Next Steps:**")
        next_steps_default = response_templates.get('next_steps_default', [
            "Ask me to use any of these tools",
            "Request specific file operations", 
            "Ask for help with data analysis"
        ])
        
        try:
            server_tools = self.get_available_tools()
            
            response_parts = []
            response_parts.append(tools_info_header)
            response_parts.append("")
            
            for tool in server_tools:
                tool_name = tool.get('name', 'unknown')
                description = tool.get('description', 'No description available')
                
                response_parts.append(f"**{tool_name}:** {description}")
                response_parts.append("")
            
            response_parts.append(next_steps_header)
            for step in next_steps_default:
                response_parts.append(f"- {step}")
            
            return "\n".join(response_parts)
        except Exception as e:
            print(f"⚠️  Could not get tools from server: {e}")
            # Fallback to configuration
            tools = self.config.get('tools', {})
            
            response_parts = []
            response_parts.append(tools_info_header)
            response_parts.append("")
            
            for tool_name, tool_config in tools.items():
                if isinstance(tool_config, dict):
                    description = tool_config.get('description', 'No description available')
                    keywords = tool_config.get('keywords', [])
                    when_to_use = tool_config.get('when_to_use', '')
                    
                    response_parts.append(f"**{tool_name}:** {description}")
                    if keywords:
                        response_parts.append(f"  Keywords: {', '.join(keywords)}")
                    if when_to_use:
                        response_parts.append(f"  When to use: {when_to_use}")
                    response_parts.append("")
                else:
                    response_parts.append(f"**{tool_name}:** {tool_config}")
                    response_parts.append("")
            
            response_parts.append(next_steps_header)
            for step in next_steps_default:
                response_parts.append(f"- {step}")
            
            return "\n".join(response_parts)
    
    def ask_llm_what_to_do(self, query: str) -> tuple[List[str], Dict[str, Dict[str, Any]]]:
        """Ask the LLM to decide which tools to use and what arguments to extract."""
        # Get available tools from server
        try:
            server_tools = self.get_available_tools()
            tool_info = []
            
            for tool in server_tools:
                tool_name = tool.get('name', 'unknown')
                description = tool.get('description', 'No description')
                
                # Get parameter information from server
                param_info = self.get_tool_parameters_from_server(tool_name)
                
                if param_info:
                    tool_info.append(f"- {tool_name}: {description}\n  Parameters:\n" + "\n".join(param_info))
                else:
                    tool_info.append(f"- {tool_name}: {description}")
        except Exception as e:
            print(f"⚠️  Could not get tools from server: {e}")
            # Fallback to configuration
            tools = self.config.get('tools', {})
            tool_selection = self.config.get('tool_selection', {})
            
            tool_info = []
            for tool_name, tool_config in tool_selection.items():
                description = tool_config.get('description', 'No description')
                
                # Get parameter information from server
                param_info = self.get_tool_parameters_from_server(tool_name)
                
                if param_info:
                    tool_info.append(f"- {tool_name}: {description}\n  Parameters:\n" + "\n".join(param_info))
                else:
                    tool_info.append(f"- {tool_name}: {description}")
        
        # Get LLM reasoning configuration
        llm_reasoning_config = self.config.get('llm_reasoning', {})
        system_prompt_template = llm_reasoning_config.get('system_prompt_template', 
            "You are an AI assistant that helps users with file system operations.\n\nAvailable tools:\n{tools}\n\nYour task is to select appropriate tools and extract arguments.")
        user_prompt_template = llm_reasoning_config.get('user_prompt_template', "User query: {query}\n\nRespond with JSON only:")
        json_extraction_regex = llm_reasoning_config.get('json_extraction_regex', r'\{.*\}')
        
        # Format the system prompt with available tools
        system_prompt = system_prompt_template.format(tools="\n".join(tool_info))
        user_prompt = user_prompt_template.format(query=query)
        
        # Call the LLM to decide what to do
        try:
            import requests
            import json
            
            # Get LLM configuration
            llm_config = self.config.get('llm', {})
            model = llm_config.get('model', 'phi3:mini')
            provider = llm_config.get('provider', 'ollama')
            api_url = llm_config.get('api_url', 'http://localhost:11434/api/generate')
            timeout = llm_config.get('timeout', 30)
            options = llm_config.get('options', {'temperature': 0.1, 'top_p': 0.9})
            
            # Try to generate schema from server first, fallback to config
            json_schema = self.generate_json_schema_from_server()
            if not json_schema:
                # Fallback to config schema if available
                json_schema = llm_config.get('json_schema')
            
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
            
            print(f"🤖 Calling LLM ({provider}:{model})...")
            response = requests.post(api_url, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', '').strip()
                print(f"🤖 LLM Response: {llm_response}")
                
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
                            import re
                            json_match = re.search(json_extraction_regex, llm_response, re.DOTALL)
                            if json_match:
                                llm_json = json.loads(json_match.group())
                            else:
                                print(f"❌ Could not extract JSON from response")
                                print(f"🤖 Raw response: {llm_response}")
                                return [], {}
                    
                    # Handle new step-based plan format
                    if 'plan' in llm_json:
                        plan = llm_json.get('plan', [])
                        selected_tools = [step.get('tool') for step in plan if step.get('tool')]
                        arguments = {step.get('tool'): step.get('arguments', {}) for step in plan if step.get('tool')}
                        return selected_tools, arguments
                    else:
                        # Legacy format support
                        selected_tools = llm_json.get('tools', [])
                        arguments = llm_json.get('arguments', {})
                        return selected_tools, arguments
                    
                except Exception as e:
                    print(f"❌ Failed to parse LLM JSON response: {e}")
                    print(f"🤖 Raw response: {llm_response}")
                    return [], {}
                    
            else:
                print(f"❌ LLM API error: {response.status_code}")
                return [], {}
                
        except Exception as e:
            print(f"❌ Error calling LLM: {e}")
            return [], {}
    
    def process_query(self, query: str) -> str:
        """Process a user query using the configured behavior."""
        print(f"🤖 Processing query: {query}")
        print(f"📋 Using configuration: {self.config_path}")
        
        # Show LLM model information
        llm_config = self.config.get('llm', {})
        model = llm_config.get('model', 'Unknown')
        provider = llm_config.get('provider', 'Unknown')
        print(f"🧠 Using LLM: {model} ({provider})")
        
        # Check for meta-questions about tools
        query_lower = query.lower()
        tool_meta_keywords = ['tools available', 'what tools', 'available tools', 'list tools', 'show tools']
        if any(keyword in query_lower for keyword in tool_meta_keywords):
            # Handle meta-question about available tools
            return self.generate_tools_info_response()
        
        # Let the LLM decide what to do
        selected_tools, arguments = self.ask_llm_what_to_do(query)
        
        if selected_tools:
            print(f"🛠️  LLM selected tools: {' → '.join(selected_tools)}")
            if arguments:
                print(f"📝 LLM extracted arguments: {arguments}")
            
            # Execute the selected tools with arguments
            results = self.execute_sequence_with_arguments(selected_tools, arguments)
            return self.generate_response(query, results)
        else:
            # LLM didn't select any tools, show available tools
            try:
                server_tools = self.get_available_tools()
                tool_names = [tool.get('name') for tool in server_tools]
                print(f"🛠️  Available tools: {', '.join(tool_names)}")
            except:
                tools = self.config.get('tools', {})
                print(f"🛠️  Available tools: {', '.join(tools.keys())}")
            print(f"💡 Tip: Be specific about what you want me to do")
            return self.generate_tools_info_response()

def main():
    """Main function for testing."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python llm_client.py <config.yaml> [query]")
        print("Example: python llm_client.py llm_client_config.yaml 'What data is available?'")
        return
    
    config_path = sys.argv[1]
    query = sys.argv[2] if len(sys.argv) > 2 else "What data is available?"
    
    try:
        client = LLMClient(config_path)
        response = client.process_query(query)
        print("\n" + "="*50)
        print("🤖 LLM Response:")
        print("="*50)
        print(response)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 