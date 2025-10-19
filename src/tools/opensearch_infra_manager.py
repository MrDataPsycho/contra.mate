#!/usr/bin/env python3
"""
OpenSearch Infrastructure Manager - Tool for managing OpenSearch indices.

Provides commands for creating, deleting, listing indices and viewing statistics.

Usage:
    # Create index with default settings
    uv run python src/tools/opensearch_infra_manager.py create --index contracts-v1

    # Create index with force recreate
    uv run python src/tools/opensearch_infra_manager.py create --index contracts-v1 --force-recreate

    # List all indices
    uv run python src/tools/opensearch_infra_manager.py list

    # Get stats for specific index
    uv run python src/tools/opensearch_infra_manager.py stats --index contracts-v1

    # Delete index
    uv run python src/tools/opensearch_infra_manager.py delete --index contracts-test

    # Check cluster health
    uv run python src/tools/opensearch_infra_manager.py health
"""

from typing import Optional

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from contramate.services.opensearch_infra_service import create_opensearch_infra_service
from contramate.utils.settings.factory import settings_factory

app = typer.Typer(help="OpenSearch Infrastructure Manager")
console = Console()


@app.command()
def create(
    index_name: Optional[str] = typer.Option(
        None,
        "--index",
        "-i",
        help="OpenSearch index name (uses default from settings if not provided)"
    ),
    vector_dimension: Optional[int] = typer.Option(
        None,
        "--vector-dim",
        "-d",
        help="Vector dimension for embeddings (uses value from APP_VECTOR_DIMENSION if not provided)"
    ),
    force_recreate: bool = typer.Option(
        False,
        "--force-recreate",
        "-f",
        help="Delete existing index and recreate"
    )
):
    """Create OpenSearch index with proper mappings for platinum models"""

    console.print("\n[cyan]Initializing OpenSearch infrastructure service...[/cyan]")
    try:
        infra_service = create_opensearch_infra_service()

        # Get cluster health
        health = infra_service.get_cluster_health()
        console.print(f"[cyan]OpenSearch cluster status: {health.get('status')}[/cyan]")

        if not health.get("healthy"):
            console.print(f"[red]✗ OpenSearch cluster is not healthy: {health}[/red]")
            return

        # Use default index name if not provided
        target_index = index_name or infra_service.app_config.default_index_name
        vector_dim = vector_dimension or infra_service.app_config.vector_dimension

        console.print(f"\n[bold cyan]Creating index: {target_index}[/bold cyan]")
        console.print(f"[cyan]Vector dimension: {vector_dim}[/cyan]")
        console.print(f"[cyan]Force recreate: {force_recreate}[/cyan]\n")

        # Create index
        success = infra_service.create_index(
            index_name=target_index,
            vector_dimension=vector_dim,
            force_recreate=force_recreate
        )

        if success:
            console.print(f"\n[green]✓ Successfully created index: {target_index}[/green]")

            # Get index stats
            stats = infra_service.get_index_stats(target_index)
            console.print(f"\n[bold cyan]Index Stats:[/bold cyan]")
            console.print(f"  Health: {stats.get('health')}")
            console.print(f"  Status: {stats.get('status')}")
            console.print(f"  Total documents: {stats.get('total_documents')}")
            console.print(f"  Index size: {stats.get('index_size')}")
        else:
            console.print(f"\n[red]✗ Failed to create index: {target_index}[/red]")

    except Exception as e:
        console.print(f"[red]Error creating index: {e}[/red]")
        return


@app.command()
def delete(
    index_name: str = typer.Option(
        ...,
        "--index",
        "-i",
        help="OpenSearch index name to delete",
        prompt="Enter index name to delete"
    ),
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt"
    )
):
    """Delete an OpenSearch index"""

    if not confirm:
        confirmed = typer.confirm(f"Are you sure you want to delete index '{index_name}'?")
        if not confirmed:
            console.print("[yellow]Deletion cancelled[/yellow]")
            return

    console.print(f"\n[cyan]Deleting index: {index_name}[/cyan]")

    try:
        infra_service = create_opensearch_infra_service()

        success = infra_service.delete_index(index_name)

        if success:
            console.print(f"[green]✓ Successfully deleted index: {index_name}[/green]")
        else:
            console.print(f"[red]✗ Failed to delete index: {index_name}[/red]")

    except Exception as e:
        console.print(f"[red]Error deleting index: {e}[/red]")


@app.command()
def list():
    """List all available OpenSearch indices with statistics"""

    console.print("\n[cyan]Fetching OpenSearch indices...[/cyan]\n")

    try:
        infra_service = create_opensearch_infra_service()

        # Get list of indices
        indices = infra_service.list_indices()

        if not indices:
            console.print("[yellow]No indices found[/yellow]")
            return

        # Create table
        table = Table(title="OpenSearch Indices", show_header=True, header_style="bold cyan")
        table.add_column("Index Name", style="cyan")
        table.add_column("Health", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Documents", justify="right")
        table.add_column("Size", justify="right")

        # Get stats for each index
        for index_name in sorted(indices):
            # Skip system indices
            if index_name.startswith('.'):
                continue

            stats = infra_service.get_index_stats(index_name)

            # Color code health
            health = stats.get('health', 'unknown')
            if health == 'green':
                health_display = f"[green]{health}[/green]"
            elif health == 'yellow':
                health_display = f"[yellow]{health}[/yellow]"
            elif health == 'red':
                health_display = f"[red]{health}[/red]"
            else:
                health_display = f"[dim]{health}[/dim]"

            table.add_row(
                index_name,
                health_display,
                stats.get('status', 'unknown'),
                str(stats.get('total_documents', 0)),
                stats.get('index_size', 'unknown')
            )

        console.print(table)
        console.print(f"\n[dim]Total indices: {len([i for i in indices if not i.startswith('.')])}\n[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing indices: {e}[/red]")


@app.command()
def stats(
    index_name: Optional[str] = typer.Option(
        None,
        "--index",
        "-i",
        help="OpenSearch index name (uses default from settings if not provided)"
    )
):
    """Get detailed statistics for a specific index"""

    try:
        infra_service = create_opensearch_infra_service()

        # Use default index name if not provided
        target_index = index_name or infra_service.app_config.default_index_name

        console.print(f"\n[cyan]Fetching stats for index: {target_index}[/cyan]\n")

        stats = infra_service.get_index_stats(target_index)

        if not stats.get('exists'):
            console.print(f"[red]✗ Index '{target_index}' does not exist[/red]")
            if stats.get('error'):
                console.print(f"[red]Error: {stats.get('error')}[/red]")
            return

        # Display stats
        console.print(f"[bold cyan]Index: {target_index}[/bold cyan]")
        console.print(f"  Health: {stats.get('health')}")
        console.print(f"  Status: {stats.get('status')}")
        console.print(f"  Total documents: {stats.get('total_documents')}")
        console.print(f"  Index size: {stats.get('index_size')}\n")

    except Exception as e:
        console.print(f"[red]Error getting index stats: {e}[/red]")


@app.command()
def health():
    """Check OpenSearch cluster health"""

    console.print("\n[cyan]Checking OpenSearch cluster health...[/cyan]\n")

    try:
        infra_service = create_opensearch_infra_service()

        health = infra_service.get_cluster_health()

        if health.get('error'):
            console.print(f"[red]✗ Error connecting to OpenSearch: {health.get('error')}[/red]")
            return

        # Color code status
        status = health.get('status', 'unknown')
        if status == 'green':
            status_display = f"[green]{status}[/green]"
        elif status == 'yellow':
            status_display = f"[yellow]{status}[/yellow]"
        elif status == 'red':
            status_display = f"[red]{status}[/red]"
        else:
            status_display = f"[dim]{status}[/dim]"

        console.print(f"[bold cyan]Cluster Health[/bold cyan]")
        console.print(f"  Cluster name: {health.get('cluster_name')}")
        console.print(f"  Status: {status_display}")
        console.print(f"  Version: {health.get('version')}")
        console.print(f"  Number of nodes: {health.get('number_of_nodes')}")
        console.print(f"  Number of data nodes: {health.get('number_of_data_nodes')}")
        console.print(f"  Active primary shards: {health.get('active_primary_shards')}")
        console.print(f"  Active shards: {health.get('active_shards')}")
        console.print(f"  Relocating shards: {health.get('relocating_shards')}")
        console.print(f"  Initializing shards: {health.get('initializing_shards')}")
        console.print(f"  Unassigned shards: {health.get('unassigned_shards')}")

        if health.get('healthy'):
            console.print(f"\n[green]✓ Cluster is healthy[/green]\n")
        else:
            console.print(f"\n[red]✗ Cluster is not healthy[/red]\n")

    except Exception as e:
        console.print(f"[red]Error checking cluster health: {e}[/red]")


if __name__ == "__main__":
    app()
