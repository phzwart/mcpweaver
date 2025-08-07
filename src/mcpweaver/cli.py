"""Console script for mcpweaver."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from pathlib import Path
import sys

from .generic_mcp_server import GenericMCPServer, validate_config, test_tool, run_server
from .llm_client import LLMClient
from .mcp_client_cli import run_interactive_mode

app = typer.Typer(help="MCP Weaver - YAML configurable MCP Server/Client tools")
console = Console()


@app.command()
def server(
    config_path: str = typer.Argument(..., help="Path to YAML configuration file"),
    host: str = typer.Option("localhost", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8080, "--port", "-p", help="Port to bind to"),
    validate_only: bool = typer.Option(False, "--validate", help="Only validate config, don't start server"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output including full MCP tool definitions")
):
    """Start an MCP server from YAML configuration."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        console.print(f"[red]❌ Configuration file not found: {config_path}[/red]")
        raise typer.Exit(1)
    
    try:
        if validate_only:
            console.print(f"[yellow]🔍 Validating configuration: {config_path}[/yellow]")
            success = validate_config(config_path)
            if success:
                console.print("[green]✅ Configuration is valid![/green]")
            else:
                console.print("[red]❌ Configuration validation failed![/red]")
                raise typer.Exit(1)
        else:
            console.print(f"[green]🚀 Starting MCP server with config: {config_path}[/green]")
            console.print(f"[blue]📍 Server will be available at: http://{host}:{port}[/blue]")
            if verbose:
                console.print("[yellow]🔍 Verbose mode enabled - showing full tool definitions[/yellow]")
            run_server(config_path, host, port, verbose)
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def client(
    config_path: str = typer.Argument(..., help="Path to client YAML configuration file"),
    query: str = typer.Argument(None, help="Query to process"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Run in interactive mode")
):
    """Run MCP client with YAML configuration."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        console.print(f"[red]❌ Configuration file not found: {config_path}[/red]")
        raise typer.Exit(1)
    
    try:
        client_instance = LLMClient(config_path)
        
        if interactive:
            console.print("[green]🤖 Starting interactive mode...[/green]")
            run_interactive_mode(client_instance)
        elif query:
            console.print(f"[blue]🤖 Processing query: {query}[/blue]")
            response = client_instance.process_query(query)
            console.print("\n" + "="*50)
            console.print("[bold green]🤖 Response:[/bold green]")
            console.print("="*50)
            console.print(response)
        else:
            # Default query - could be made configurable in the future
            default_query = "What's the magic word?"
            console.print(f"[blue]🤖 Using default query: {default_query}[/blue]")
            response = client_instance.process_query(default_query)
            console.print("\n" + "="*50)
            console.print("[bold green]🤖 Response:[/bold green]")
            console.print("="*50)
            console.print(response)
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def validate(
    config_path: str = typer.Argument(..., help="Path to YAML configuration file")
):
    """Validate YAML configuration file."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        console.print(f"[red]❌ Configuration file not found: {config_path}[/red]")
        raise typer.Exit(1)
    
    try:
        console.print(f"[yellow]🔍 Validating configuration: {config_path}[/yellow]")
        success = validate_config(config_path)
        
        if success:
            console.print("[green]✅ Configuration is valid![/green]")
        else:
            console.print("[red]❌ Configuration validation failed![/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def test(
    config_path: str = typer.Argument(..., help="Path to YAML configuration file"),
    tool_name: str = typer.Argument(..., help="Name of tool to test")
):
    """Test a specific tool from configuration."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        console.print(f"[red]❌ Configuration file not found: {config_path}[/red]")
        raise typer.Exit(1)
    
    try:
        console.print(f"[yellow]🧪 Testing tool '{tool_name}' from config: {config_path}[/yellow]")
        success = test_tool(config_path, tool_name)
        
        if success:
            console.print(f"[green]✅ Tool '{tool_name}' test passed![/green]")
        else:
            console.print(f"[red]❌ Tool '{tool_name}' test failed![/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def info(
    config_path: str = typer.Argument(..., help="Path to YAML configuration file")
):
    """Show information about configuration and available tools."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        console.print(f"[red]❌ Configuration file not found: {config_path}[/red]")
        raise typer.Exit(1)
    
    try:
        console.print(f"[blue] Configuration info: {config_path}[/blue]")
        
        # Try to load as server config
        try:
            server = GenericMCPServer(config_path)
            console.print(f"[green]✅ Server configuration loaded successfully[/green]")
            console.print(f"[blue] Loaded {len(server.tools)} tools:[/blue]")
            
            table = Table(title="Available Tools")
            table.add_column("Tool Name", style="cyan")
            table.add_column("Python Path", style="magenta")
            table.add_column("Description", style="green")
            
            for tool_name, tool_info in server.tools.items():
                table.add_row(
                    tool_name,
                    tool_info['python_path'],
                    tool_info['description'][:50] + "..." if len(tool_info['description']) > 50 else tool_info['description']
                )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[yellow]⚠️  Not a valid server config: {e}[/yellow]")
        
        # Try to load as client config
        try:
            client = LLMClient(config_path)
            console.print(f"[green]✅ Client configuration loaded successfully[/green]")
            
            # Show client config info
            config = client.config
            console.print(f"[blue] LLM: {config.get('llm', {}).get('model', 'Unknown')} ({config.get('llm', {}).get('provider', 'Unknown')})[/blue]")
            console.print(f"[blue]🌐 MCP Server: {config.get('mcp_server', {}).get('host', 'Unknown')}:{config.get('mcp_server', {}).get('port', 'Unknown')}[/blue]")
            
            tools = config.get('tools', {})
            if tools:
                console.print(f"[blue]🛠️  Configured {len(tools)} tools:[/blue]")
                for tool_name, tool_config in tools.items():
                    if isinstance(tool_config, dict):
                        desc = tool_config.get('description', 'No description')
                        console.print(f"  - {tool_name}: {desc}")
                    else:
                        console.print(f"  - {tool_name}: {tool_config}")
            
        except Exception as e:
            console.print(f"[yellow]⚠️  Not a valid client config: {e}[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def init(
    output_dir: str = typer.Option(".", "--output", "-o", help="Output directory for example files")
):
    """Initialize example configuration files."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    try:
        console.print(f"[green]📁 Creating example files in: {output_path}[/green]")
        
        # Copy example client config
        from .example_client_config import create_example_config
        client_config_path = output_path / "client_config.yaml"
        create_example_config(client_config_path)
        console.print(f"[green]✅ Created: {client_config_path}[/green]")
        
        # Create example server config
        server_config_path = output_path / "tools_config.yaml"
        create_example_server_config(server_config_path)
        console.print(f"[green]✅ Created: {server_config_path}[/green]")
        
        console.print("\n[bold green]🎉 Example files created![/bold green]")
        console.print("\n[blue]Next steps:[/blue]")
        console.print("1. Edit the configuration files to match your needs")
        console.print("2. Start the server: mcpweaver server tools_config.yaml")
        console.print("3. Run the client: mcpweaver client client_config.yaml 'What data is available?'")
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


def create_example_server_config(output_path: Path):
    """Create an example server configuration file."""
    config_content = """# Example Tools Configuration
# This file defines the tools available to the MCP server

tools:
  list_files:
    python_path: "file_tools.list_files"
    full_path: "examples/file_system_surfer/tools"
    workflow_context:
      description: "List files in a directory with optional pattern matching"
  
  read_file:
    python_path: "file_tools.read_file"
    full_path: "examples/file_system_surfer/tools"
    workflow_context:
      description: "Read contents of a file with optional line limit"
  
  count_lines:
    python_path: "file_tools.count_lines"
    full_path: "examples/file_system_surfer/tools"
    workflow_context:
      description: "Count lines in a file"
  
  get_file_info:
    python_path: "file_tools.get_file_info"
    full_path: "examples/file_system_surfer/tools"
    workflow_context:
      description: "Get detailed information about a file"
  
  search_files:
    python_path: "file_tools.search_files"
    full_path: "examples/file_system_surfer/tools"
    workflow_context:
      description: "Search for files with optional content search"
"""
    output_path.write_text(config_content)


if __name__ == "__main__":
    app()
