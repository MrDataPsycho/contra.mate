#!/usr/bin/env python3
"""
Tool to test OpenSearch Vector Search Service capabilities.

This tool demonstrates various search types:
1. Semantic search (vector similarity)
2. Text search (full-text with filters)
3. Hybrid search (combined semantic + text)
4. Project-specific search
5. Document similarity search
6. Document chunk retrieval

Usage:
    uv run python src/tools/test_search.py semantic "contract termination"
    uv run python src/tools/test_search.py text "important legal terms" --filters '{"project_id": ["test-project"]}'
    uv run python src/tools/test_search.py hybrid "contract termination clause"
    uv run python src/tools/test_search.py project test-project
    uv run python src/tools/test_search.py similar some-record-id
"""

import json
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from contramate.services import (
    OpenSearchVectorSearchServiceFactory,
    SearchResponse,
)

app = typer.Typer(help="Test OpenSearch Vector Search Service capabilities")
console = Console()


def print_search_results(response: SearchResponse, detailed: bool = False):
    """Print search results in a formatted table."""
    if not response.results:
        console.print("[yellow]No results found[/yellow]")
        return
    
    # Create summary panel
    summary_text = f"""
[bold]Search Summary[/bold]
• Query: {response.query}
• Type: {response.search_type}
• Results: {len(response.results)}/{response.total_results}
• Execution Time: {response.execution_time_ms:.1f}ms
"""
    
    if response.filters:
        summary_text += f"• Filters: {response.filters}\n"
    
    if response.semantic_weight and response.text_weight:
        summary_text += f"• Weights: semantic={response.semantic_weight}, text={response.text_weight}\n"
    
    console.print(Panel(summary_text.strip(), title="Search Results", expand=False))
    
    # Create results table
    if detailed:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Score", style="cyan", width=8)
        table.add_column("Project", style="green", width=12)
        table.add_column("Document", style="blue", width=20)
        table.add_column("Chunk", style="yellow", width=8)
        table.add_column("Content", style="white", width=50)
        table.add_column("Hierarchy", style="dim", width=30)
    else:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Score", style="cyan", width=8)
        table.add_column("Document", style="blue", width=30)
        table.add_column("Content Preview", style="white", width=60)
    
    for i, result in enumerate(response.results[:10]):  # Limit to first 10 results
        content_preview = result.content[:100] + "..." if len(result.content) > 100 else result.content
        
        if detailed:
            table.add_row(
                f"{result.score:.3f}",
                result.project_id[:12] + "..." if len(result.project_id) > 12 else result.project_id,
                result.document_title[:20] + "..." if len(result.document_title) > 20 else result.document_title,
                f"{result.chunk_index}",
                content_preview,
                str(result.section_hierarchy)[:30] + "..." if result.section_hierarchy and len(str(result.section_hierarchy)) > 30 else str(result.section_hierarchy) or ""
            )
        else:
            table.add_row(
                f"{result.score:.3f}",
                result.document_title[:30] + "..." if len(result.document_title) > 30 else result.document_title,
                content_preview
            )
    
    console.print(table)


@app.command()
def semantic(
    query: str,
    k: int = typer.Option(10, "--k", help="Number of nearest neighbors"),
    size: int = typer.Option(5, "--size", help="Number of results to return"),
    min_score: float = typer.Option(0.5, "--min-score", help="Minimum similarity score"),
    filters: Optional[str] = typer.Option(None, "--filters", help="JSON string of filters"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed results"),
):
    """Perform semantic search using vector similarity."""
    console.print(f"[bold]Semantic Search:[/bold] '{query}'")
    
    # Parse filters if provided
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            console.print("[red]Error: Invalid JSON in filters[/red]")
            raise typer.Exit(1)
    
    # Create search service and perform search
    search_service = OpenSearchVectorSearchServiceFactory.create_default()
    result = search_service.semantic_search(
        query=query,
        k=k,
        size=size,
        min_score=min_score,
        filters=filter_dict
    )
    
    if result.is_err():
        console.print(f"[red]Error: {result.err()}[/red]")
        raise typer.Exit(1)
    
    print_search_results(result.unwrap(), detailed=detailed)


@app.command()
def text(
    query: str,
    size: int = typer.Option(5, "--size", help="Number of results to return"),
    fields: Optional[str] = typer.Option(None, "--fields", help="Comma-separated list of fields to search"),
    filters: Optional[str] = typer.Option(None, "--filters", help="JSON string of filters"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed results"),
):
    """Perform text-based search using full-text search."""
    console.print(f"[bold]Text Search:[/bold] '{query}'")
    
    # Parse filters if provided
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            console.print("[red]Error: Invalid JSON in filters[/red]")
            raise typer.Exit(1)
    
    # Parse fields if provided
    field_list = None
    if fields:
        field_list = [f.strip() for f in fields.split(",")]
    
    # Create search service and perform search
    search_service = OpenSearchVectorSearchServiceFactory.create_default()
    result = search_service.text_search(
        query=query,
        size=size,
        fields=field_list,
        filters=filter_dict
    )
    
    if result.is_err():
        console.print(f"[red]Error: {result.err()}[/red]")
        raise typer.Exit(1)
    
    print_search_results(result.unwrap(), detailed=detailed)


@app.command()
def hybrid(
    query: str,
    size: int = typer.Option(5, "--size", help="Number of results to return"),
    semantic_weight: float = typer.Option(0.7, "--semantic-weight", help="Weight for semantic search"),
    text_weight: float = typer.Option(0.3, "--text-weight", help="Weight for text search"),
    min_score: float = typer.Option(0.5, "--min-score", help="Minimum combined score"),
    filters: Optional[str] = typer.Option(None, "--filters", help="JSON string of filters"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed results"),
):
    """Perform hybrid search combining semantic and text search."""
    console.print(f"[bold]Hybrid Search:[/bold] '{query}'")
    
    # Parse filters if provided
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            console.print("[red]Error: Invalid JSON in filters[/red]")
            raise typer.Exit(1)
    
    # Create search service and perform search
    search_service = OpenSearchVectorSearchServiceFactory.create_default()
    result = search_service.hybrid_search(
        query=query,
        size=size,
        semantic_weight=semantic_weight,
        text_weight=text_weight,
        min_score=min_score,
        filters=filter_dict
    )
    
    if result.is_err():
        console.print(f"[red]Error: {result.err()}[/red]")
        raise typer.Exit(1)
    
    print_search_results(result.unwrap(), detailed=detailed)


@app.command()
def project(
    project_id: str,
    query: Optional[str] = typer.Option(None, "--query", help="Optional search query within project"),
    search_type: str = typer.Option("hybrid", "--type", help="Search type: semantic, text, or hybrid"),
    size: int = typer.Option(10, "--size", help="Number of results to return"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed results"),
):
    """Search within a specific project."""
    if query:
        console.print(f"[bold]Project Search:[/bold] '{query}' in project '{project_id}'")
    else:
        console.print(f"[bold]Project Browse:[/bold] All documents in project '{project_id}'")
    
    # Create search service and perform search
    search_service = OpenSearchVectorSearchServiceFactory.create_default()
    result = search_service.search_by_project(
        project_id=project_id,
        query=query,
        search_type=search_type,
        size=size
    )
    
    if result.is_err():
        console.print(f"[red]Error: {result.err()}[/red]")
        raise typer.Exit(1)
    
    print_search_results(result.unwrap(), detailed=detailed)


@app.command()
def similar(
    record_id: str,
    size: int = typer.Option(5, "--size", help="Number of similar documents to return"),
    filters: Optional[str] = typer.Option(None, "--filters", help="JSON string of filters"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed results"),
):
    """Find documents similar to a given document."""
    console.print(f"[bold]Similarity Search:[/bold] Documents similar to '{record_id}'")
    
    # Parse filters if provided
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            console.print("[red]Error: Invalid JSON in filters[/red]")
            raise typer.Exit(1)
    
    # Create search service and perform search
    search_service = OpenSearchVectorSearchServiceFactory.create_default()
    result = search_service.search_similar_documents(
        record_id=record_id,
        size=size,
        filters=filter_dict
    )
    
    if result.is_err():
        console.print(f"[red]Error: {result.err()}[/red]")
        raise typer.Exit(1)
    
    print_search_results(result.unwrap(), detailed=detailed)


@app.command()
def document(
    project_id: str,
    reference_doc_id: str,
    size: Optional[int] = typer.Option(None, "--size", help="Maximum number of chunks to return"),
    detailed: bool = typer.Option(True, "--detailed/--simple", help="Show detailed results"),
):
    """Retrieve all chunks from a specific document."""
    console.print(f"[bold]Document Chunks:[/bold] '{reference_doc_id}' in project '{project_id}'")
    
    # Create search service and perform search
    search_service = OpenSearchVectorSearchServiceFactory.create_default()
    result = search_service.search_by_document(
        project_id=project_id,
        reference_doc_id=reference_doc_id,
        size=size
    )
    
    if result.is_err():
        console.print(f"[red]Error: {result.err()}[/red]")
        raise typer.Exit(1)
    
    print_search_results(result.unwrap(), detailed=detailed)


@app.command()
def demo():
    """Run a comprehensive demonstration of all search capabilities."""
    console.print("[bold cyan]🔍 OpenSearch Vector Search Service Demo[/bold cyan]\n")
    
    search_service = OpenSearchVectorSearchServiceFactory.create_default()
    
    # Demo 1: Semantic Search
    console.print("[bold]1. Semantic Search Demo[/bold]")
    result = search_service.semantic_search("contract termination", size=3)
    if result.is_ok():
        print_search_results(result.unwrap())
    else:
        console.print(f"[red]Error: {result.err()}[/red]")
    
    console.print("\n" + "="*60 + "\n")
    
    # Demo 2: Text Search with Filters
    console.print("[bold]2. Text Search with Filters Demo[/bold]")
    filters = {"project_id": ["test-project"]}
    result = search_service.text_search("important terms", size=3, filters=filters)
    if result.is_ok():
        print_search_results(result.unwrap())
    else:
        console.print(f"[red]Error: {result.err()}[/red]")
    
    console.print("\n" + "="*60 + "\n")
    
    # Demo 3: Hybrid Search
    console.print("[bold]3. Hybrid Search Demo[/bold]")
    result = search_service.hybrid_search("legal conditions", size=3)
    if result.is_ok():
        print_search_results(result.unwrap())
    else:
        console.print(f"[red]Error: {result.err()}[/red]")
    
    console.print("\n[bold green]🎉 Demo completed![/bold green]")


if __name__ == "__main__":
    app()