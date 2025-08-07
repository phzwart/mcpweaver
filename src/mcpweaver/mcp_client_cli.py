"""
CLI wrapper for the MCP LLM client.

Usage:
    python -m agentbx.mcp.mcp_client_cli <config.yaml> [query]
    python -m agentbx.mcp.mcp_client_cli <config.yaml> --interactive
"""

import sys
import argparse
from pathlib import Path

from .llm_client import LLMClient

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="MCP LLM Client CLI")
    parser.add_argument("config_path", help="Path to YAML configuration file")
    parser.add_argument("query", nargs="?", help="Query to process")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    
    args = parser.parse_args()
    
    # Check if config file exists
    config_path = Path(args.config_path)
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        sys.exit(1)
    
    try:
        client = LLMClient(str(config_path))
        
        if args.interactive:
            run_interactive_mode(client)
        elif args.query:
            response = client.process_query(args.query)
            print("\n" + "="*50)
            print("🤖 LLM Response:")
            print("="*50)
            print(response)
        else:
            # Default query
            response = client.process_query("What data is available in Redis?")
            print("\n" + "="*50)
            print("🤖 LLM Response:")
            print("="*50)
            print(response)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def run_interactive_mode(client: LLMClient):
    """Run the client in interactive mode."""
    print("🤖 MCP LLM Client - Interactive Mode")
    print("="*50)
    print("Type your queries (or 'quit' to exit):")
    print()
    
    while True:
        try:
            query = input("🤖 Query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not query:
                continue
            
            print()
            response = client.process_query(query)
            print("\n" + "="*50)
            print("🤖 Response:")
            print("="*50)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print()

if __name__ == "__main__":
    main() 