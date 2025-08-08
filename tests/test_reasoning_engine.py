"""
Unit tests for the ReasoningEngine.

These tests verify the pure reasoning functionality without requiring
any external servers or LLM APIs.
"""

import json
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src directory to the path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcpweaver.reasoning_engine import ReasoningEngine


class TestReasoningEngine:
    """Test cases for the ReasoningEngine class."""
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration for testing."""
        return {
            'llm': {
                'model': 'phi3:mini',
                'provider': 'ollama',
                'api_url': 'http://localhost:11434/api/generate',
                'timeout': 30,
                'options': {
                    'temperature': 0.1,
                    'top_p': 0.9
                }
            },
            'reasoning': {
                'system_prompt_template': 'You are an AI assistant. Available tools:\n{tools}',
                'user_prompt_template': 'User query: {query}',
                'json_extraction_regex': r'\{.*\}'
            },
            'response_format': {
                'include_confidence': True,
                'include_reasoning': True,
                'max_tools_per_query': 5
            }
        }
    
    @pytest.fixture
    def sample_tools(self):
        """Create sample tools for testing."""
        return [
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
            },
            {
                "name": "calculator",
                "description": "Perform mathematical calculations",
                "parameters": {
                    "expression": {"type": "string", "description": "Math expression", "required": True},
                    "precision": {"type": "integer", "description": "Decimal precision", "required": False, "default": 2}
                }
            }
        ]
    
    def test_init_with_config(self, sample_config):
        """Test initialization with configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_path = f.name
        
        try:
            engine = ReasoningEngine(config_path)
            assert engine.config == sample_config
            assert engine.config_path == Path(config_path)
        finally:
            Path(config_path).unlink()
    
    def test_load_config_file_not_found(self):
        """Test initialization with non-existent config file."""
        with pytest.raises(FileNotFoundError):
            ReasoningEngine("non_existent_config.yaml")
    
    def test_generate_json_schema(self, sample_config, sample_tools):
        """Test JSON schema generation from tool definitions."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_path = f.name
        
        try:
            engine = ReasoningEngine(config_path)
            schema = engine.generate_json_schema(sample_tools)
            
            # Check basic schema structure (plan-based)
            assert schema is not None
            assert schema["type"] == "object"
            assert "plan" in schema["properties"]
            assert schema["properties"]["plan"]["type"] == "array"
            assert "confidence" in schema["properties"]
            
        finally:
            Path(config_path).unlink()
    
    def test_generate_json_schema_empty_tools(self, sample_config):
        """Test JSON schema generation with empty tools list."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_path = f.name
        
        try:
            engine = ReasoningEngine(config_path)
            schema = engine.generate_json_schema([])
            assert schema is None
        finally:
            Path(config_path).unlink()
    
    def test_convert_python_type_to_json(self, sample_config):
        """Test Python type to JSON schema type conversion."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_path = f.name
        
        try:
            engine = ReasoningEngine(config_path)
            
            # Test various type conversions
            assert engine._convert_python_type_to_json("string") == "string"
            assert engine._convert_python_type_to_json("str") == "string"
            assert engine._convert_python_type_to_json("integer") == "integer"
            assert engine._convert_python_type_to_json("int") == "integer"
            assert engine._convert_python_type_to_json("number") == "number"
            assert engine._convert_python_type_to_json("float") == "number"
            assert engine._convert_python_type_to_json("boolean") == "boolean"
            assert engine._convert_python_type_to_json("bool") == "boolean"
            assert engine._convert_python_type_to_json("array") == "array"
            assert engine._convert_python_type_to_json("list") == "array"
            assert engine._convert_python_type_to_json("object") == "object"
            assert engine._convert_python_type_to_json("dict") == "object"
            assert engine._convert_python_type_to_json("Any") == "string"
            assert engine._convert_python_type_to_json("unknown") == "string"
            
        finally:
            Path(config_path).unlink()
    
    @patch('requests.post')
    def test_reason_about_query_success(self, mock_post, sample_config, sample_tools):
        """Test successful reasoning about a query."""
        # Mock successful LLM response (tools/arguments -> will be normalized to plan)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': json.dumps({
                'tools': ['np_mean', 'np_std'],
                'arguments': {
                    'np_mean': {'a': [1, 2, 3, 4, 5]},
                    'np_std': {'a': [1, 2, 3, 4, 5]}
                },
                'reasoning': 'User wants both central tendency and spread measures',
                'confidence': 0.95
            })
        }
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_path = f.name
        
        try:
            engine = ReasoningEngine(config_path)
            plan = engine.reason_about_query("Calculate mean and std of [1,2,3,4,5]", sample_tools)
            
            # Check the plan structure (step-based)
            assert 'plan' in plan
            assert isinstance(plan['plan'], list)
            assert len(plan['plan']) == 2
            assert plan['plan'][0]['tool'] == 'np_mean'
            assert plan['plan'][0]['arguments'].get('a') == [1, 2, 3, 4, 5]
            assert plan['plan'][1]['tool'] == 'np_std'
            assert plan['plan'][1]['arguments'].get('a') == [1, 2, 3, 4, 5]
            assert plan['confidence'] == 0.95
            
            # Verify the LLM was called with correct parameters
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['model'] == 'phi3:mini'
            assert 'format' in payload
            assert 'json_schema' in payload['options']
            
        finally:
            Path(config_path).unlink()
    
    @patch('requests.post')
    def test_reason_about_query_llm_error(self, mock_post, sample_config, sample_tools):
        """Test reasoning when LLM API returns an error."""
        # Mock LLM API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_path = f.name
        
        try:
            engine = ReasoningEngine(config_path)
            plan = engine.reason_about_query("Calculate mean", sample_tools)
            
            # Check error response (plan format)
            assert plan['plan'] == []
            assert plan['confidence'] == 0.0
            assert 'error' in plan
            assert 'LLM API error: 500' in plan['error']
            
        finally:
            Path(config_path).unlink()
    
    @patch('requests.post')
    def test_reason_about_query_parse_error(self, mock_post, sample_config, sample_tools):
        """Test reasoning when LLM response cannot be parsed."""
        # Mock LLM response with invalid JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'This is not valid JSON'
        }
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_path = f.name
        
        try:
            engine = ReasoningEngine(config_path)
            plan = engine.reason_about_query("Calculate mean", sample_tools)
            
            # Check error response (plan format)
            assert plan['plan'] == []
            assert plan['confidence'] == 0.0
            assert 'error' in plan
            assert 'Failed to parse response' in plan['error']
            
        finally:
            Path(config_path).unlink()
    
    def test_call_llm_success(self, sample_config):
        """Test successful LLM call."""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'response': 'Test response'}
            mock_post.return_value = mock_response
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(sample_config, f)
                config_path = f.name
            
            try:
                engine = ReasoningEngine(config_path)
                response = engine._call_llm("Test prompt")
                assert response == 'Test response'
                
            finally:
                Path(config_path).unlink()
    
    def test_call_llm_with_schema(self, sample_config):
        """Test LLM call with JSON schema."""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'response': 'Test response'}
            mock_post.return_value = mock_response
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(sample_config, f)
                config_path = f.name
            
            try:
                engine = ReasoningEngine(config_path)
                schema = {"type": "object", "properties": {}}
                response = engine._call_llm("Test prompt", schema)
                assert response == 'Test response'
                
                # Verify schema was included in request
                call_args = mock_post.call_args
                payload = call_args[1]['json']
                assert payload['format'] == 'json'
                assert payload['options']['json_schema'] == schema
                
            finally:
                Path(config_path).unlink()
    
    def test_call_llm_error(self, sample_config):
        """Test LLM call with API error."""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(sample_config, f)
                config_path = f.name
            
            try:
                engine = ReasoningEngine(config_path)
                with pytest.raises(Exception, match="LLM API error: 500"):
                    engine._call_llm("Test prompt")
                    
            finally:
                Path(config_path).unlink()
    
    def test_parse_llm_response_with_schema(self, sample_config):
        """Test parsing LLM response with schema."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_path = f.name
        
        try:
            engine = ReasoningEngine(config_path)
            schema = {"type": "object", "properties": {}}
            response = '{"plan": [{"tool": "test", "arguments": {}, "why": "because"}], "confidence": 0.8}'
            
            result = engine._parse_llm_response(response, schema)
            assert result == {"plan": [{"tool": "test", "arguments": {}, "why": "because"}], "confidence": 0.8}

        finally:
            Path(config_path).unlink()
    
    def test_parse_llm_response_without_schema(self, sample_config):
        """Test parsing LLM response without schema."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_path = f.name
        
        try:
            engine = ReasoningEngine(config_path)
            response = '{"plan": [{"tool": "test", "arguments": {}, "why": "because"}], "confidence": 0.8}'
            
            result = engine._parse_llm_response(response)
            assert result == {"plan": [{"tool": "test", "arguments": {}, "why": "because"}], "confidence": 0.8}
            
        finally:
            Path(config_path).unlink()
    
    def test_parse_llm_response_regex_fallback(self, sample_config):
        """Test parsing LLM response with regex fallback."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_path = f.name
        
        try:
            engine = ReasoningEngine(config_path)
            response = 'Some text before {"plan": [{"tool": "test", "arguments": {}, "why": "because"}], "confidence": 0.8} and some text after'
            
            result = engine._parse_llm_response(response)
            assert result == {"plan": [{"tool": "test", "arguments": {}, "why": "because"}], "confidence": 0.8}
            
        finally:
            Path(config_path).unlink()
    
    def test_parse_llm_response_parse_error(self, sample_config):
        """Test parsing LLM response with parse error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_path = f.name
        
        try:
            engine = ReasoningEngine(config_path)
            response = 'This is not valid JSON at all'
            
            with pytest.raises(Exception, match="Could not extract JSON from response"):
                engine._parse_llm_response(response)
                
        finally:
            Path(config_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__]) 