"""Example tool implementations for demonstration."""

import random
import time
from typing import Dict, Any, List

def check_health() -> Dict[str, Any]:
    """Check if the system is healthy."""
    # Simulate health check
    time.sleep(0.1)
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": random.randint(100, 1000),
        "memory_usage": random.uniform(0.1, 0.8)
    }

def list_data() -> List[Dict[str, Any]]:
    """List available data items."""
    # Simulate data listing
    time.sleep(0.2)
    return [
        {"id": "item_1", "name": "Sample Data 1", "type": "text", "size": 1024},
        {"id": "item_2", "name": "Sample Data 2", "type": "json", "size": 2048},
        {"id": "item_3", "name": "Sample Data 3", "type": "csv", "size": 512},
        {"id": "item_4", "name": "Sample Data 4", "type": "xml", "size": 4096}
    ]

def get_data(data_id: str = None) -> Dict[str, Any]:
    """Get specific data by ID."""
    if not data_id:
        # Get random data if no ID provided
        data_items = list_data()
        data_id = random.choice(data_items)["id"]
    
    # Simulate data retrieval
    time.sleep(0.3)
    
    sample_data = {
        "item_1": {"content": "This is sample text data", "metadata": {"created": "2024-01-01"}},
        "item_2": {"content": {"key": "value", "nested": {"data": "example"}}, "metadata": {"created": "2024-01-02"}},
        "item_3": {"content": "name,age,city\nJohn,30,NYC\nJane,25,LA", "metadata": {"created": "2024-01-03"}},
        "item_4": {"content": "<root><item>XML data</item></root>", "metadata": {"created": "2024-01-04"}}
    }
    
    return sample_data.get(data_id, {"error": f"Data with ID '{data_id}' not found"})

def analyze_data(data_id: str = None) -> Dict[str, Any]:
    """Analyze data contents and structure."""
    if not data_id:
        # Get random data if no ID provided
        data_items = list_data()
        data_id = random.choice(data_items)["id"]
    
    # Simulate data analysis
    time.sleep(0.4)
    
    data = get_data(data_id)
    if "error" in data:
        return {"error": f"Could not analyze data: {data['error']}"}
    
    content = data["content"]
    
    # Analyze based on content type
    if isinstance(content, str):
        if content.startswith("name,age,city"):
            # CSV data
            lines = content.split("\n")
            return {
                "type": "csv",
                "rows": len(lines) - 1,  # Exclude header
                "columns": len(lines[0].split(",")),
                "sample": lines[:3]
            }
        elif content.startswith("<"):
            # XML data
            return {
                "type": "xml",
                "size": len(content),
                "has_root": "<root>" in content,
                "elements": content.count("<") // 2
            }
        else:
            # Text data
            return {
                "type": "text",
                "length": len(content),
                "words": len(content.split()),
                "lines": len(content.split("\n"))
            }
    elif isinstance(content, dict):
        # JSON data
        return {
            "type": "json",
            "keys": list(content.keys()),
            "nested_levels": _count_nested_levels(content),
            "sample": content
        }
    else:
        return {
            "type": "unknown",
            "content_type": type(content).__name__
        }

def _count_nested_levels(obj, current_level=0):
    """Count the maximum nesting level in a JSON object."""
    if not isinstance(obj, dict):
        return current_level
    
    max_level = current_level
    for value in obj.values():
        if isinstance(value, dict):
            max_level = max(max_level, _count_nested_levels(value, current_level + 1))
    
    return max_level 