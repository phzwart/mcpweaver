"""
Special prompt generator function for MCP Weaver.
This function is registered as a tool but pulls prompts from server config.
"""

from typing import List, Dict, Any
import yaml
from pathlib import Path


def generate_context(tools: List[Dict[str, Any]], config_path: str = None) -> str:
    """Generate context about tools by pulling prompts from server config.
    
    Args:
        tools: List of available tools with their definitions
        config_path: Path to server config YAML file
        
    Returns:
        Context string about tool relationships and usage patterns
    """
    if not config_path:
        return ""
    
    try:
        # Load prompts from server config
        config_file = Path(config_path)
        if not config_file.exists():
            return ""
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Get prompts from config
        prompts = config.get('prompts', {})
        context_parts = []
        
        # Add general context
        if 'general_context' in prompts:
            context_parts.append(prompts['general_context'])
        
        # Add tool-specific context
        if 'tool_context' in prompts:
            tool_context = prompts['tool_context']
            for tool in tools:
                tool_name = tool['name']
                if tool_name in tool_context:
                    context_parts.append(f"{tool_name}: {tool_context[tool_name]}")
        
        # Add workflow patterns
        if 'workflows' in prompts:
            workflows = prompts['workflows']
            context_parts.append("\nCommon workflows:")
            for workflow_name, workflow_desc in workflows.items():
                context_parts.append(f"- {workflow_name}: {workflow_desc}")
        
        # Add query-specific hints
        if 'query_hints' in prompts:
            hints = prompts['query_hints']
            context_parts.append("\nQuery hints:")
            for pattern, hint in hints.items():
                context_parts.append(f"- {pattern}: {hint}")
        
        return "\n".join(context_parts)
        
    except Exception as e:
        return f"Error loading prompts: {e}"


def analyze_tool_relationships(tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze relationships between tools.
    
    Args:
        tools: List of available tools
        
    Returns:
        Dictionary with tool relationships and patterns
    """
    analysis = {
        'categories': {},
        'workflows': [],
        'dependencies': {}
    }
    
    # Categorize tools by prefix
    for tool in tools:
        name = tool['name']
        if name.startswith('np_'):
            if 'numpy' not in analysis['categories']:
                analysis['categories']['numpy'] = []
            analysis['categories']['numpy'].append(name)
        elif name.startswith('torch_'):
            if 'pytorch' not in analysis['categories']:
                analysis['categories']['pytorch'] = []
            analysis['categories']['pytorch'].append(name)
    
    # Identify common workflows
    if 'numpy' in analysis['categories'] and 'pytorch' in analysis['categories']:
        analysis['workflows'].append({
            'name': 'Array to Tensor Pipeline',
            'steps': ['torch_tensor', 'torch_mean'],
            'description': 'Convert arrays to tensors then compute statistics'
        })
    
    if 'numpy' in analysis['categories']:
        analysis['workflows'].append({
            'name': 'Statistical Analysis',
            'steps': ['np_mean', 'np_std', 'np_sum'],
            'description': 'Compute various statistics on arrays'
        })
    
    return analysis 