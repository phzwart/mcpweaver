"""Helper module for creating example client configurations."""

def create_example_config(output_path):
    """Create an example client configuration file."""
    config_content = """# Example Client Configuration
# This shows how to configure the client for any MCP server

llm:
  model: "gpt-4"
  provider: "openai"     # ollama, openai, anthropic, etc.
  
mcp_server:
  host: "localhost"
  port: 8080

# Behavior and Prompt Instructions
behavior:
  role: "MCP Assistant"
  personality: "Helpful, analytical, and thorough"
  
  instructions: |
    You are an MCP assistant that helps users explore and analyze data.
    
    When users ask questions:
    1. Use the appropriate tools based on the query
    2. Build logical sequences of tool calls
    3. Provide clear explanations of what you're doing and why
    4. Follow the configured workflow patterns
    
    Always explain your reasoning and what tools you're using.

# Default tool sequence (always run these first)
default_sequence:
  - "list_files"  # List current directory files

# Tool Usage Guidelines with Keywords
tools:
  list_files:
    description: "List files in a directory"
    keywords: ["list", "files", "directory", "folder", "ls", "dir"]
    when_to_use: "Use to see what files are available in a directory"
    
  read_file:
    description: "Read file contents"
    keywords: ["read", "file", "content", "view", "show", "cat"]
    when_to_use: "Use to read and display file contents"
    
  count_lines:
    description: "Count lines in a file"
    keywords: ["count", "lines", "wc", "length", "size"]
    when_to_use: "Use to count lines, empty lines, and code lines in a file"
    
  get_file_info:
    description: "Get file information"
    keywords: ["info", "information", "details", "stat", "metadata"]
    when_to_use: "Use to get detailed information about a file"
    
  search_files:
    description: "Search for files"
    keywords: ["search", "find", "grep", "pattern", "match"]
    when_to_use: "Use to search for files by pattern or content"

# Prompt Templates
prompts:
  system_prompt: |
    You are an MCP assistant. You have access to tools through an MCP server.
    
    Your job is to help users explore and analyze data. Always:
    - Start by checking system health
    - Use appropriate tools to answer questions
    - Explain what you're doing and why
    - Provide clear, helpful responses
    
  user_prompt_template: |
    User Query: {query}
    
    Available Tools:
    - list_files: List files in a directory
    - read_file: Read file contents
    - count_lines: Count lines in a file
    - get_file_info: Get file information
    - search_files: Search for files
    
    Please use the appropriate tools to answer the user's query.

# Response Format Configuration
response_format:
  include_tool_calls: true
  explain_reasoning: true
  provide_summary: true
  suggest_next_steps: true

# Summary Logic (configurable per tool)
summary_logic:
  list_files:
    success_message: "✅ Found files in directory"
    failure_message: "📭 No files found in directory"
  
  read_file:
    success_message: "✅ File read successfully"
    failure_message: "❌ Could not read file"

# Next Steps Suggestions
next_steps:
  - "Ask me to read a specific file"
  - "Request information about any file"
  - "Ask me to count lines in a file"
  - "Request to search for files with specific patterns"

# Argument Extraction Rules
argument_extraction:
  read_file:
    file_path:
      from_tool: "list_files"
      field: "path"
      type: "first"  # random, first, direct
  
  count_lines:
    file_path:
      from_tool: "list_files"
      field: "path"
      type: "first"
  
  get_file_info:
    file_path:
      from_tool: "list_files"
      field: "path"
      type: "first"
"""
    output_path.write_text(config_content) 