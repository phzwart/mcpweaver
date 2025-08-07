# Abstract Reasoning Engine

The `AbstractReasoningEngine` is a specialized version of the reasoning engine that performs **symbolic reasoning** about tool selection and argument extraction without requiring concrete data values.

## Overview

The AbstractReasoningEngine allows you to reason about tools and arguments using **symbolic references** like `<numpy array named A>` instead of concrete data values like `[1,2,3,4,5]`. This is particularly useful for:

- **Planning**: Reason about what tools to use before having actual data
- **Analysis**: Understand data structures and their relationships
- **Documentation**: Generate execution plans with symbolic references
- **Teaching**: Demonstrate tool usage patterns without concrete examples

### Key Features

- **Symbolic References**: Use placeholders like `<numpy array named A>` in queries and arguments
- **Data Structure Descriptions**: Provide metadata about data without concrete values
- **Abstract Reasoning**: Reason about tools and arguments without actual data
- **Symbolic Context**: Include descriptions of available data structures
- **Reference Extraction**: Automatically identify symbolic references in arguments

## Quick Start

```python
from mcpweaver import AbstractReasoningEngine

# Initialize with configuration
engine = AbstractReasoningEngine("configs/abstract_reasoning_config.yaml")

# Define available tools
available_tools = [
    {
        "name": "np_mean",
        "description": "Calculate arithmetic mean of array elements",
        "parameters": {
            "a": {"type": "array", "description": "Input array", "required": True}
        }
    }
]

# Define symbolic data structures (descriptions without concrete values)
symbolic_data_structures = {
    "A": {
        "type": "numpy_array",
        "shape": "(100, 3)",
        "dtype": "float64",
        "description": "Feature matrix with 100 samples and 3 features"
    }
}

# Create symbolic mapping
symbolic_mapping = engine.create_symbolic_data_mapping(symbolic_data_structures)

# Get abstract execution plan
plan = engine.reason_about_query(
    query="Compute the mean of <numpy array named A>",
    available_tools=available_tools,
    symbolic_data=symbolic_mapping
)

print(plan)
# Output:
# {
#     "tools": ["np_mean"],
#     "arguments": {"a": "<numpy array named A>"},
#     "reasoning": "The user wants to calculate the arithmetic mean...",
#     "confidence": 1.0,
#     "symbolic_references": ["<numpy array named A>"]
# }
```

## Symbolic References

The AbstractReasoningEngine supports various types of symbolic references:

### Basic Format
```
<type named name>
```

### Examples

| Type | Reference | Description |
|------|-----------|-------------|
| NumPy Array | `<numpy array named A>` | Array variable named A |
| Pandas DataFrame | `<dataframe named df>` | DataFrame variable named df |
| List | `<list named data>` | List variable named data |
| Generic Variable | `<variable named x>` | Any variable named x |

### Data Structure Descriptions

When creating symbolic mappings, you can provide rich descriptions:

```python
symbolic_data_structures = {
    "A": {
        "type": "numpy_array",
        "shape": "(100, 3)",
        "dtype": "float64",
        "description": "Feature matrix with 100 samples and 3 features"
    },
    "B": {
        "type": "pandas_dataframe",
        "shape": "(1000, 5)",
        "description": "Dataframe with 1000 rows and 5 columns"
    },
    "C": {
        "type": "list",
        "length": "200",
        "description": "List of 200 data points"
    }
}
```

## API Reference

### AbstractReasoningEngine

#### `__init__(config_path: str)`

Initialize the abstract reasoning engine with a configuration file.

**Parameters:**
- `config_path`: Path to the YAML configuration file

#### `reason_about_query(query: str, available_tools: List[Dict], symbolic_data: Optional[Dict] = None) -> Dict`

Main abstract reasoning method that returns an execution plan with symbolic references.

**Parameters:**
- `query`: User's natural language query (can contain symbolic references)
- `available_tools`: List of available tools with their definitions
- `symbolic_data`: Optional mapping of symbolic names to data descriptions

**Returns:**
```python
{
    "tools": List[str],           # Tool names to execute
    "arguments": Dict[str, Dict], # Arguments for each tool (with symbolic refs)
    "reasoning": str,             # Explanation of reasoning
    "confidence": float,          # Confidence level (0.0 to 1.0)
    "symbolic_references": List[str], # Symbolic references found in arguments
    "error": str                  # Error message if something went wrong
}
```

#### `create_symbolic_data_mapping(data_structures: Dict[str, Any]) -> Dict[str, str]`

Create a mapping of symbolic names to data descriptions.

**Parameters:**
- `data_structures`: Dictionary of data structures with their descriptions

**Returns:**
- Mapping of symbolic names to descriptions

#### `_extract_symbolic_references(arguments: Dict[str, Any]) -> List[str]`

Extract symbolic references from arguments.

**Parameters:**
- `arguments`: The arguments dictionary

**Returns:**
- List of symbolic references found in arguments

## Configuration

The AbstractReasoningEngine uses a specialized configuration that emphasizes symbolic reasoning:

```yaml
# abstract_reasoning_config.yaml
llm:
  model: "phi3:mini"
  provider: "ollama" 
  api_url: "http://localhost:11434/api/generate"
  timeout: 30
  options:
    temperature: 0.1
    top_p: 0.9

reasoning:
  system_prompt_template: |
    You are an AI assistant that performs abstract reasoning about tool selection and argument extraction.
    
    Available tools:
    {tools}
    
    Your task is to:
    1. Understand what the user wants to accomplish
    2. Select the appropriate tool(s) to use
    3. Extract arguments using symbolic references (e.g., <numpy array named A>)
    4. Provide clear reasoning about your choices
    
    IMPORTANT: Use symbolic references in your arguments instead of concrete values.
    Examples of symbolic references:
    - <numpy array named A> for a numpy array variable named A
    - <dataframe named df> for a pandas dataframe named df
    - <list named data> for a list variable named data
    - <variable named x> for any variable named x
    
    Respond with a JSON object containing:
    - "tools": Array of tool names to use (in order of execution)
    - "arguments": Object with arguments for each tool (use symbolic references)
    - "reasoning": Explanation of your logic and choices
    - "confidence": Confidence level (0.0 to 1.0)
  
  user_prompt_template: "User query: {query}"
  json_extraction_regex: r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'

response_format:
  include_confidence: true
  include_reasoning: true
  include_symbolic_references: true
  max_tools_per_query: 5
```

## Examples

### Basic Symbolic Reasoning

```python
from mcpweaver import AbstractReasoningEngine

engine = AbstractReasoningEngine("configs/abstract_reasoning_config.yaml")

tools = [
    {
        "name": "np_mean",
        "description": "Calculate arithmetic mean of array elements",
        "parameters": {
            "a": {"type": "array", "description": "Input array", "required": True}
        }
    }
]

symbolic_data = {
    "A": {
        "type": "numpy_array",
        "shape": "(100, 3)",
        "dtype": "float64"
    }
}

symbolic_mapping = engine.create_symbolic_data_mapping(symbolic_data)

plan = engine.reason_about_query(
    "Compute the mean of <numpy array named A>",
    tools,
    symbolic_mapping
)
```

### Complex Symbolic Reasoning

```python
# Multiple data structures
symbolic_data = {
    "features": {
        "type": "numpy_array",
        "shape": "(1000, 10)",
        "dtype": "float64",
        "description": "Feature matrix with 1000 samples and 10 features"
    },
    "targets": {
        "type": "numpy_array",
        "shape": "(1000,)",
        "dtype": "int32",
        "description": "Target values with 1000 samples"
    },
    "df": {
        "type": "pandas_dataframe",
        "shape": "(500, 5)",
        "description": "Dataframe with 500 rows and 5 columns"
    }
}

# Complex query with multiple symbolic references
plan = engine.reason_about_query(
    "Compute the correlation between <numpy array named features> and <numpy array named targets>",
    tools,
    symbolic_mapping
)
```

### Symbolic Reference Extraction

```python
# Test arguments with symbolic references
test_args = {
    "np_mean": {"a": "<numpy array named A>"},
    "np_std": {"a": "<numpy array named B>"},
    "np_corrcoef": {
        "x": "<numpy array named A>",
        "y": "<numpy array named C>"
    }
}

symbolic_refs = engine._extract_symbolic_references(test_args)
print(symbolic_refs)
# Output: ['<numpy array named A>', '<numpy array named B>', '<numpy array named C>']
```

## Use Cases

### 1. Planning and Design

Use abstract reasoning to plan data analysis workflows before having actual data:

```python
# Plan analysis workflow
plan = engine.reason_about_query(
    "Analyze the correlation between features and targets, then compute summary statistics",
    available_tools,
    symbolic_mapping
)
```

### 2. Documentation Generation

Generate execution plans for documentation without concrete examples:

```python
# Generate documentation examples
plan = engine.reason_about_query(
    "Compute the mean and standard deviation of <dataframe named df>",
    available_tools,
    symbolic_mapping
)
```

### 3. Teaching and Learning

Demonstrate tool usage patterns with symbolic references:

```python
# Teaching example
plan = engine.reason_about_query(
    "Show me how to compute basic statistics on <numpy array named data>",
    available_tools,
    symbolic_mapping
)
```

### 4. Data Structure Analysis

Reason about data structures and their relationships:

```python
# Analyze data structure relationships
plan = engine.reason_about_query(
    "Compare the distributions of <numpy array named A> and <numpy array named B>",
    available_tools,
    symbolic_mapping
)
```

## Benefits

### For Data Scientists

1. **Planning**: Plan analysis workflows before data is available
2. **Documentation**: Generate examples with symbolic references
3. **Teaching**: Demonstrate concepts without concrete data
4. **Prototyping**: Design analysis pipelines abstractly

### For System Architects

1. **Workflow Design**: Design data processing workflows
2. **Tool Selection**: Choose appropriate tools for data structures
3. **Dependency Analysis**: Understand tool dependencies
4. **Resource Planning**: Plan computational requirements

### For Educators

1. **Concept Demonstration**: Show tool usage patterns
2. **Exercise Generation**: Create problems with symbolic references
3. **Assessment**: Evaluate understanding of tool selection
4. **Curriculum Design**: Structure learning materials

## Comparison with Concrete Reasoning

| Aspect | Concrete Reasoning | Abstract Reasoning |
|--------|-------------------|-------------------|
| **Data Requirements** | Needs actual data values | Only needs data descriptions |
| **Use Case** | Execution planning | Planning and analysis |
| **Output** | Concrete arguments | Symbolic references |
| **Performance** | Can be slower with large data | Fast, no data processing |
| **Memory** | Requires data in memory | Minimal memory usage |
| **Flexibility** | Limited to available data | Can reason about any structure |

## Testing

Run the abstract reasoning examples:

```bash
# Run the comprehensive example
python examples/abstract_reasoning_example.py

# Run the simple test
python examples/simple_abstract_test.py
```

## Integration with Execution

The AbstractReasoningEngine can be integrated with execution systems:

```python
# 1. Generate abstract plan
abstract_plan = engine.reason_about_query(query, tools, symbolic_mapping)

# 2. Resolve symbolic references to concrete data
concrete_plan = resolve_symbolic_references(abstract_plan, actual_data)

# 3. Execute the concrete plan
results = execute_plan(concrete_plan)
```

## Contributing

The AbstractReasoningEngine is designed to be extensible. Key areas for contribution:

1. **Additional Symbolic Reference Types**: Support for more data structure types
2. **Enhanced Context Understanding**: Better reasoning about data relationships
3. **Template Generation**: Generate code templates from abstract plans
4. **Validation**: Validate symbolic references against actual data structures
5. **Visualization**: Visual representation of abstract execution plans

## License

The AbstractReasoningEngine is part of the mcpweaver project and follows the same license terms. 