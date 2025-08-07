# Number Surfer Example

This example demonstrates how to use MCP Weaver with NumPy-based statistical analysis tools, including a configurable array type conversion system.

## Features

- **NumPy Statistical Tools**: Mean, standard deviation, quantiles, median, min/max, variance, sum
- **Random Data Generation**: Normal and uniform distributions
- **Configurable Array Conversions**: Generic conversion system for handling different array types
- **Tool Chaining**: Generate data and then analyze it in sequence

## Configuration Files

### `client_config.yaml`
Main client configuration with LLM settings, behavior, and serialization configuration.

### `tools_config.yaml`
Server-side tool definitions and serialization settings.

### Generic Conversions Configuration
The conversion system uses a generic configuration file located at `src/mcpweaver/conversions.yaml` that defines how different array types are serialized and deserialized.

## Array Type Conversion System

The conversion system allows you to define how different array types (NumPy, PyTorch, Pandas, etc.) should be handled when passed between tools.

### Key Features

1. **Generic Configuration**: All conversion rules are defined in the main package
2. **Multiple Array Types**: Support for NumPy, PyTorch, Pandas, and extensible for others
3. **Tool-Specific Rules**: Different conversion rules for different tool prefixes
4. **Argument Mapping**: Specify which arguments should be converted for each array type
5. **Error Handling**: Configurable behavior when conversions fail

### Default Configuration

The system automatically uses the default conversions file from the package. You can override this by specifying a custom conversions file in your configuration:

```yaml
serialization:
  conversions_file: "path/to/custom/conversions.yaml"
  enabled: true
  default_behavior: "string"
```

### Adding New Array Types

To add support for a new array type (e.g., TensorFlow), you can:

1. **Modify the default configuration**: Edit `src/mcpweaver/conversions.yaml`
2. **Use a custom configuration**: Create your own conversions file and reference it in your config

Example custom configuration:
```yaml
tensorflow:
  tool_prefixes: ["tf_"]
  serialize:
    enabled: true
    method: "numpy"
  deserialize:
    enabled: true
    method: "tensorflow.convert_to_tensor"
  import: "import tensorflow as tf"
  array_creator: "tf.convert_to_tensor"
  list_converter: "numpy"
```

## Running the Example

1. Start the MCP server:
```bash
python -m src.mcpweaver server examples/number_weaver/tools_config.yaml
```

2. Run the client:
```bash
python -m src.mcpweaver client examples/number_weaver/client_config.yaml "generate 10 random numbers and find their mean"
```

## Example Queries

- "generate 20 random numbers and compute the 0.25 quantile"
- "generate 5 random numbers and find their standard deviation"
- "calculate the mean of [1,2,3,4,5]"
- "generate 100 random numbers from normal distribution"

## Benefits of Generic Conversion Configuration

1. **Reusability**: Same conversion rules can be used across different projects
2. **Extensibility**: Easy to add support for new array types
3. **Maintainability**: All conversion logic centralized in one file
4. **Flexibility**: Different projects can use different conversion rules
5. **Error Handling**: Configurable behavior for conversion failures

## Troubleshooting

If you encounter the original error:
```
ufunc 'subtract' did not contain a loop with signature matching types (dtype('<U122'), dtype('<U122'))
```

This means the conversion system isn't working properly. Check:
1. The default conversions file exists at `src/mcpweaver/conversions.yaml`
2. The conversion configuration is enabled in both client and server configs
3. The tool names match the prefixes defined in the conversion rules 