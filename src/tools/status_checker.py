#!/usr/bin/env python3
"""
CLI tool to check the status of all available services in Contramate.

Usage:
    python src/tools/status_checker.py postgres
    python src/tools/status_checker.py openai
    python src/tools/status_checker.py all
"""

import asyncio
from typing import Dict, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

from contramate.services.postgres_status_service import PostgresService
from contramate.services.opensearch_status_service import OpenSearchStatusService
from contramate.services.openai_status_service import OpenAIStatusService
from contramate.services.litellm_status_service import LiteLLMStatusService
from contramate.llm import OpenAIChatClient, LiteLLMChatClient

app = typer.Typer(help="Check status of Contramate services")
console = Console()

# Service mappings with short names
SERVICE_MAPPINGS = {
    "postgres": {
        "name": "PostgreSQL",
        "service_class": PostgresService,
        "client": None
    },
    "opensearch": {
        "name": "OpenSearch",
        "service_class": OpenSearchStatusService,
        "client": None
    },
    "openai": {
        "name": "OpenAI",
        "service_class": OpenAIStatusService,
        "client": "openai"
    },
    "litellm": {
        "name": "LiteLLM",
        "service_class": LiteLLMStatusService,
        "client": "litellm"
    }
}

def create_client_instances():
    """Create and return client instances for AI services"""
    try:
        openai_client = OpenAIChatClient()
        litellm_client = LiteLLMChatClient()
        return {
            "openai": openai_client,
            "litellm": litellm_client
        }
    except Exception as e:
        console.print(f"[red]Failed to create AI clients: {e}[/red]")
        return {"openai": None, "litellm": None}

def get_status_color(status: str) -> str:
    """Get color for status display"""
    if status == "healthy":
        return "green"
    elif status in ["connection_error", "authentication_error", "error"]:
        return "red"
    elif status in ["rate_limit_error", "api_error"]:
        return "yellow"
    else:
        return "blue"

def format_status_response(service_name: str, response: Dict[str, Any]) -> Table:
    """Format service status response as a rich table"""
    table = Table(title=f"{service_name} Status", box=box.ROUNDED)
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    # Core status
    connected = response.get("connected", False)
    status = response.get("status", "unknown")

    table.add_row("Connected", "✅ Yes" if connected else "❌ No")
    table.add_row("Status", Text(status, style=get_status_color(status)))
    table.add_row("Message", response.get("message", "N/A"))

    # Service-specific info
    if "host" in response:
        table.add_row("Host", response["host"])
    if "port" in response:
        table.add_row("Port", str(response["port"]))
    if "database" in response:
        table.add_row("Database", response["database"])
    if "model" in response:
        table.add_row("Model", response["model"])
    if "provider" in response:
        table.add_row("Provider", response["provider"])
    if "endpoint_url" in response:
        table.add_row("Endpoint", response["endpoint_url"])

    # Usage info for AI services
    if "usage" in response and response["usage"]:
        usage = response["usage"]
        if isinstance(usage, dict):
            table.add_row("Tokens Used", f"{usage.get('total_tokens', 0)}")

    # Error info
    if "error" in response:
        table.add_row("Error", Text(response["error"], style="red"))

    return table

async def check_service_status(service_key: str, clients: Dict[str, Any]) -> Dict[str, Any]:
    """Check status of a single service

    Returns:
        Dict with status information (unwrapped from Result type)
    """
    service_config = SERVICE_MAPPINGS.get(service_key)
    if not service_config:
        return {
            "connected": False,
            "status": "error",
            "message": f"Unknown service: {service_key}"
        }

    try:
        # Create service instance with appropriate client
        if service_config["client"]:
            client = clients.get(service_config["client"])
            if not client:
                return {
                    "connected": False,
                    "status": "error",
                    "message": f"Failed to create {service_config['client']} client"
                }
            service = service_config["service_class"](client=client)
        else:
            service = service_config["service_class"]()

        # Check status - returns Result[Ok, Err]
        result = await service.check_status()

        # Unwrap Result type - both Ok and Err contain the status dict
        return result.unwrap()

    except Exception as e:
        return {
            "connected": False,
            "status": "error",
            "message": f"Failed to check {service_config['name']} status: {str(e)}"
        }

@app.command()
def check(
    service: str = typer.Argument(
        help="Service to check (postgres, opensearch, openai, litellm, all)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output")
):
    """Check status of specified service(s)"""

    async def run_checks():
        # Create AI clients
        clients = create_client_instances()

        if service.lower() == "all":
            # Check all services
            console.print("[bold blue]Checking all services...[/bold blue]\n")

            summary_table = Table(title="Service Status Summary", box=box.ROUNDED)
            summary_table.add_column("Service", style="cyan")
            summary_table.add_column("Status", style="magenta")
            summary_table.add_column("Message", style="yellow")

            for service_key, service_config in SERVICE_MAPPINGS.items():
                console.print(f"[cyan]Checking {service_config['name']}...[/cyan]")

                response = await check_service_status(service_key, clients)

                # Add to summary
                status_text = Text(response.get("status", "unknown"),
                                 style=get_status_color(response.get("status", "unknown")))
                summary_table.add_row(
                    service_config["name"],
                    status_text,
                    response.get("message", "N/A")[:50] + "..." if len(response.get("message", "")) > 50 else response.get("message", "N/A")
                )

                # Show detailed info if verbose
                if verbose:
                    detailed_table = format_status_response(service_config["name"], response)
                    console.print(detailed_table)
                    console.print()

            console.print(summary_table)

        else:
            # Check single service
            if service.lower() not in SERVICE_MAPPINGS:
                console.print(f"[red]Unknown service: {service}[/red]")
                console.print(f"Available services: {', '.join(SERVICE_MAPPINGS.keys())}")
                raise typer.Exit(1)

            service_config = SERVICE_MAPPINGS[service.lower()]
            console.print(f"[cyan]Checking {service_config['name']} status...[/cyan]\n")

            response = await check_service_status(service.lower(), clients)

            # Show detailed table
            table = format_status_response(service_config["name"], response)
            console.print(table)

            # Exit with error code if service is not healthy
            if not response.get("connected", False):
                raise typer.Exit(1)

    # Run async function
    try:
        asyncio.run(run_checks())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def list_services():
    """List all available services"""
    table = Table(title="Available Services", box=box.ROUNDED)
    table.add_column("Short Name", style="cyan")
    table.add_column("Full Name", style="magenta")
    table.add_column("Type", style="yellow")

    for key, config in SERVICE_MAPPINGS.items():
        service_type = "AI Service" if config["client"] else "Database/Search"
        table.add_row(key, config["name"], service_type)

    console.print(table)

if __name__ == "__main__":
    app()