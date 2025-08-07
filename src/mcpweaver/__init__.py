"""
MCP (Model Context Protocol) integration for agentbx.
Fresh start for natural language to function calling.
"""

__version__ = "0.1.0"

# Export the main classes
from .llm_client import LLMClient
from .reasoning_engine import ReasoningEngine
from .abstract_reasoning_engine import AbstractReasoningEngine

# Export utility functions
from .utils import (
    get_mcp_tools,
    call_mcp_tool,
    create_reasoning_engine,
    quick_reasoning_engine,
    convert_mcp_tools_to_reasoning_format
)

__all__ = [
    "LLMClient", 
    "ReasoningEngine", 
    "AbstractReasoningEngine",
    "get_mcp_tools",
    "call_mcp_tool", 
    "create_reasoning_engine",
    "quick_reasoning_engine",
    "convert_mcp_tools_to_reasoning_format"
]