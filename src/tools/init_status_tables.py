#!/usr/bin/env python3
"""
Initialize document processing status tables in the database.

Creates all status tracking tables for the document processing pipeline:
- document_conversion_status (PDF → Markdown)
- document_chunking_status (Markdown → Chunks)
- document_metadata_extraction_status (Markdown → Metadata)
- document_indexing_status (Chunks → Vector Index)

Usage:
    uv run python src/tools/init_status_tables.py
"""

import typer
from rich.console import Console
from sqlmodel import SQLModel, create_engine

from contramate.dbs.models.document_status import (
    DocumentConversionStatus,
    DocumentChunkingStatus,
    DocumentMetadataExtractionStatus,
    DocumentIndexingStatus,
)
from contramate.dbs.models.contract import ContractEsmd
from contramate.utils.settings.factory import settings_factory

app = typer.Typer(help="Initialize document processing status and metadata tables")
console = Console()


@app.command()
def init(
    drop_existing: bool = typer.Option(
        False,
        "--drop-existing",
        help="Drop existing tables before creating (WARNING: deletes all data)"
    )
):
    """Initialize all status tracking tables"""

    # Get database connection
    postgres_settings = settings_factory.create_postgres_settings()
    connection_string = postgres_settings.connection_string

    console.print(f"[cyan]Connecting to database...[/cyan]")
    console.print(f"[dim]{connection_string.split('@')[1] if '@' in connection_string else 'localhost'}[/dim]\n")

    engine = create_engine(connection_string, echo=False)

    try:
        if drop_existing:
            console.print("[yellow]⚠ Dropping existing tables...[/yellow]")
            SQLModel.metadata.drop_all(
                engine,
                tables=[
                    DocumentConversionStatus.__table__,
                    DocumentChunkingStatus.__table__,
                    DocumentMetadataExtractionStatus.__table__,
                    DocumentIndexingStatus.__table__,
                    ContractEsmd.__table__,
                ]
            )
            console.print("[green]✓ Existing tables dropped[/green]\n")

        console.print("[cyan]Creating tables...[/cyan]")

        # Create all tables
        SQLModel.metadata.create_all(
            engine,
            tables=[
                DocumentConversionStatus.__table__,
                DocumentChunkingStatus.__table__,
                DocumentMetadataExtractionStatus.__table__,
                DocumentIndexingStatus.__table__,
                ContractEsmd.__table__,
            ]
        )

        console.print("\n[bold green]✓ Tables initialized successfully![/bold green]\n")
        console.print("[cyan]Created tables:[/cyan]")
        console.print("  • document_conversion_status (PDF → Markdown status)")
        console.print("  • document_chunking_status (Markdown → Chunks status)")
        console.print("  • document_metadata_extraction_status (Metadata extraction status)")
        console.print("  • document_indexing_status (Chunks → Vector Index status)")
        console.print("  • contracting_esmd (Contract metadata storage)")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error initializing tables:[/bold red]")
        console.print(f"[red]{str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def verify():
    """Verify that status tables exist and show their structure"""

    postgres_settings = settings_factory.create_postgres_settings()
    connection_string = postgres_settings.connection_string
    engine = create_engine(connection_string, echo=False)

    console.print("[cyan]Verifying status tables...[/cyan]\n")

    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)

        tables_to_check = [
            "document_conversion_status",
            "document_chunking_status",
            "document_metadata_extraction_status",
            "document_indexing_status",
            "contracting_esmd",
        ]

        for table_name in tables_to_check:
            if inspector.has_table(table_name):
                columns = inspector.get_columns(table_name)
                console.print(f"[green]✓ {table_name}[/green]")
                console.print(f"  Columns: {', '.join([c['name'] for c in columns])}")
                console.print()
            else:
                console.print(f"[red]✗ {table_name} does not exist[/red]\n")

    except Exception as e:
        console.print(f"[red]Error verifying tables: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
