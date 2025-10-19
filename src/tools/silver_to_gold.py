#!/usr/bin/env python3
"""
Tool to chunk markdown documents from silver/ to gold/.

Pipeline:
1. Read markdown from silver layer
2. Chunk using MarkdownChunkingService
3. Save chunked documents to gold layer as JSON

Tracks processing status in document_chunking_status table.

Usage:
    uv run python src/tools/chunk_documents.py chunk
    uv run python src/tools/chunk_documents.py chunk --limit 10
    uv run python src/tools/chunk_documents.py verify
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlmodel import Session, create_engine, select

from contramate.dbs.models.contract import ContractAsmd
from contramate.dbs.models.document_status import (
    DocumentChunkingStatus,
    ProcessingStatus,
)
from contramate.models import DocumentInfo
from contramate.services.markdown_chunking_service import MarkdownChunkingService, EncodingName
from contramate.utils.settings.factory import settings_factory

app = typer.Typer(help="Chunk markdown documents to gold layer with optional enrichment")
console = Console()

# Paths
SILVER_BASE_PATH = Path("data/silver")
GOLD_BASE_PATH = Path("data/gold")


def find_markdown_file(project_id: str, reference_doc_id: str) -> Optional[Path]:
    """
    Find markdown file in silver directory.

    Args:
        project_id: Project identifier
        reference_doc_id: Document identifier

    Returns:
        Path to markdown file or None if not found
    """
    doc_dir = SILVER_BASE_PATH / project_id / reference_doc_id

    if not doc_dir.exists():
        return None

    # Find first .md file
    md_files = list(doc_dir.glob("*.md"))
    if not md_files:
        return None

    return md_files[0]


def save_chunked_document(chunked_doc, project_id: str, reference_doc_id: str) -> Path:
    """
    Save chunked document to gold directory as JSON.

    Args:
        chunked_doc: ChunkedDocument or EnrichedDocument to save
        project_id: Project identifier
        reference_doc_id: Document identifier (internal doc ID for directory structure)

    Returns:
        Path to saved JSON file
    """
    # Create output directory: project_id/reference_doc_id/
    output_dir = GOLD_BASE_PATH / project_id / reference_doc_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save as JSON using original filename + .json (filename already has .md)
    output_path = output_dir / f"{chunked_doc.filename}.json"
    chunked_doc.save_json(output_path)

    return output_path


@app.command()
def chunk(
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Limit number of documents to process"
    ),
    skip_existing: bool = typer.Option(
        True,
        "--skip-existing/--reprocess",
        help="Skip documents that are already processed"
    ),
    token_limit: int = typer.Option(
        4000,
        "--token-limit",
        help="Maximum tokens per chunk (must be less than embedding model limit of 8192)"
    ),
    min_chunk_size: int = typer.Option(
        100,
        "--min-chunk-size",
        help="Minimum tokens for a chunk"
    ),
    enrich: bool = typer.Option(
        False,
        "--enrich/--no-enrich",
        help="Enable content enrichment using LLM (disabled by default)"
    ),
    delay_seconds: float = typer.Option(
        0.0,
        "--delay",
        "-d",
        help="Delay in seconds between processing each document (useful for API rate limits when enriching)"
    )
):
    """Chunk markdown documents with optional LLM-based enrichment and status tracking"""

    # Create database connection
    postgres_settings = settings_factory.create_postgres_settings()
    connection_string = postgres_settings.connection_string
    engine = create_engine(connection_string, echo=False)

    # Initialize LLM client for enrichment (only if enrichment is enabled)
    enrichment_service = None
    if enrich:
        console.print("[cyan]Initializing LLM client for enrichment...[/cyan]")
        try:
            from contramate.llm.factory import create_default_chat_client
            from contramate.services.enrich_content_service import EnrichmentService

            chat_client = create_default_chat_client(client_type="litellm")
            enrichment_service = EnrichmentService(client=chat_client)
            console.print("[green]✓ LLM client initialized[/green]\n")
        except Exception as e:
            console.print(f"[red]✗ Failed to initialize LLM client: {e}[/red]")
            raise typer.Exit(1)

    # Statistics
    total_documents = 0
    processed = 0
    failed = 0
    skipped = 0
    not_found = 0
    failed_details = []  # Track failed documents with details

    mode = "chunking + enrichment" if enrich else "chunking only"
    console.print(f"[cyan]Starting document processing ({mode})...[/cyan]")
    console.print(f"[cyan]Source: {SILVER_BASE_PATH}[/cyan]")
    console.print(f"[cyan]Target: {GOLD_BASE_PATH}[/cyan]")
    console.print(f"[cyan]Token limit: {token_limit}, Min chunk size: {min_chunk_size}[/cyan]")
    if delay_seconds > 0:
        console.print(f"[cyan]Delay between documents: {delay_seconds}s[/cyan]")
    console.print()

    with Session(engine) as session:
        # Get all documents from contract_asmd
        statement = select(ContractAsmd)
        if limit:
            statement = statement.limit(limit)

        contracts = session.exec(statement).all()
        total_documents = len(contracts)

        console.print(f"[cyan]Found {total_documents} documents to process[/cyan]\n")

        # Counter for progress reporting
        doc_counter = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Chunking documents...", total=total_documents)

            for contract in contracts:
                doc_counter += 1
                project_id = contract.project_id
                reference_doc_id = contract.reference_doc_id

                # Check if already processed
                if skip_existing:
                    existing_status = session.exec(
                        select(DocumentChunkingStatus).where(
                            DocumentChunkingStatus.project_id == project_id,
                            DocumentChunkingStatus.reference_doc_id == reference_doc_id,
                            DocumentChunkingStatus.status == ProcessingStatus.PROCESSED
                        )
                    ).first()

                    if existing_status:
                        skipped += 1
                        progress.update(task, advance=1)
                        continue

                # Find markdown file
                md_file = find_markdown_file(project_id, reference_doc_id)
                if not md_file:
                    not_found += 1
                    progress.update(task, advance=1)
                    continue

                # Initialize status record
                status_record = DocumentChunkingStatus(
                    project_id=project_id,
                    reference_doc_id=reference_doc_id,
                    status=ProcessingStatus.READY,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )

                # Check if status record already exists
                existing = session.exec(
                    select(DocumentChunkingStatus).where(
                        DocumentChunkingStatus.project_id == project_id,
                        DocumentChunkingStatus.reference_doc_id == reference_doc_id
                    )
                ).first()

                if existing:
                    status_record = existing
                    status_record.status = ProcessingStatus.READY
                    status_record.updated_at = datetime.now(timezone.utc)
                else:
                    session.add(status_record)

                session.commit()

                # Chunk markdown document (and optionally enrich)
                start_time = time.time()
                try:
                    # Step 1: Read markdown content
                    with open(md_file, 'r', encoding='utf-8') as f:
                        markdown_content = f.read()

                    # Step 2: Extract filename (with .md extension)
                    filename = md_file.name  # Gets filename with extension

                    # Step 3: Create DocumentInfo with filename
                    doc_info = DocumentInfo(
                        project_id=project_id,
                        reference_doc_id=reference_doc_id,
                        filename=filename,
                        contract_type=contract.contract_type or "Unknown"
                    )

                    # Step 4: Chunk document
                    chunking_service = MarkdownChunkingService(
                        markdown_content=markdown_content,
                        doc_info=doc_info,
                        encoding_name=EncodingName.DEFAULT,
                        token_limit=token_limit,
                        min_chunk_size=min_chunk_size
                    )

                    chunked_doc_result = chunking_service.execute()
                    if chunked_doc_result.is_err():
                        raise RuntimeError(f"Chunking failed: {chunked_doc_result.unwrap_err()}")

                    chunked_doc = chunked_doc_result.unwrap()

                    # Step 5: Optionally enrich chunks (async/parallel with full document context)
                    final_doc = chunked_doc
                    if enrich and enrichment_service:
                        enriched_doc_result = enrichment_service.execute(chunked_doc)
                        if enriched_doc_result.is_err():
                            raise RuntimeError(f"Enrichment failed: {enriched_doc_result.unwrap_err()}")
                        final_doc = enriched_doc_result.unwrap()

                    # Step 6: Save document (chunked or enriched)
                    save_chunked_document(final_doc, project_id, reference_doc_id)

                    execution_time = time.time() - start_time

                    # Update status to PROCESSED
                    status_record.status = ProcessingStatus.PROCESSED
                    status_record.chunk_count = final_doc.total_chunks
                    status_record.execution_time = execution_time
                    status_record.updated_at = datetime.now(timezone.utc)
                    session.add(status_record)
                    session.commit()

                    processed += 1

                    # Add delay after successful processing (useful for API rate limits when enriching)
                    if delay_seconds > 0:
                        time.sleep(delay_seconds)

                except Exception as e:
                    execution_time = time.time() - start_time

                    # Update status to FAILED
                    status_record.status = ProcessingStatus.FAILED
                    status_record.execution_time = execution_time
                    status_record.error_message = str(e)[:1000]
                    status_record.updated_at = datetime.now(timezone.utc)
                    session.add(status_record)
                    session.commit()

                    failed += 1
                    # Track failed document details
                    failed_details.append({
                        "project_id": project_id,
                        "reference_doc_id": reference_doc_id,
                        "document_title": contract.document_title or "Unknown",
                        "error": str(e)[:200]
                    })
                    console.print(f"[red]✗ Failed: {contract.document_title[:60] if contract.document_title else 'Unknown'}...[/red]")

                progress.update(task, advance=1)

                # Print progress every 10 documents
                if doc_counter % 10 == 0:
                    progress.stop()
                    console.print(f"\n[bold cyan]Progress Update:[/bold cyan]")
                    console.print(f"  Processed: {doc_counter}/{total_documents} documents")
                    console.print(f"  Success: [green]{processed}[/green] | Failed: [red]{failed}[/red] | Skipped: [yellow]{skipped}[/yellow] | Not Found: [yellow]{not_found}[/yellow]\n")
                    progress.start()

    # Print summary
    console.print("\n[bold cyan]Processing Summary:[/bold cyan]")
    console.print(f"  Total documents: {total_documents}")
    console.print(f"  Successfully processed: [green]{processed}[/green]")
    console.print(f"  Failed: [red]{failed}[/red]")
    console.print(f"  Skipped (already processed): [yellow]{skipped}[/yellow]")
    console.print(f"  Markdown files not found: [yellow]{not_found}[/yellow]")

    # Show failed document details
    if failed_details:
        console.print("\n[bold red]Failed Documents:[/bold red]")
        for idx, detail in enumerate(failed_details, 1):
            console.print(f"\n[red]{idx}. {detail['document_title'][:60]}[/red]")
            console.print(f"   Project ID: {detail['project_id']}")
            console.print(f"   Reference Doc ID: {detail['reference_doc_id']}")
            console.print(f"   Error: {detail['error']}")
            console.print(f"   Path: {SILVER_BASE_PATH / detail['project_id'] / detail['reference_doc_id']}")

    success_msg = "✓ Chunking and enrichment complete!" if enrich else "✓ Chunking complete!"
    console.print(f"\n[bold green]{success_msg}[/bold green]")
    console.print(f"[dim]Documents saved to: {GOLD_BASE_PATH}[/dim]")


@app.command()
def verify(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to show")
):
    """Verify chunking status and show sample chunked documents"""

    postgres_settings = settings_factory.create_postgres_settings()
    connection_string = postgres_settings.connection_string
    engine = create_engine(connection_string, echo=False)

    with Session(engine) as session:
        # Get status statistics
        statement = select(DocumentChunkingStatus)
        all_status = session.exec(statement).all()

        ready_count = sum(1 for s in all_status if s.status == ProcessingStatus.READY)
        processed_count = sum(1 for s in all_status if s.status == ProcessingStatus.PROCESSED)
        failed_count = sum(1 for s in all_status if s.status == ProcessingStatus.FAILED)

        console.print("[bold cyan]Chunking Status Summary:[/bold cyan]")
        console.print(f"  Total tracked: {len(all_status)}")
        console.print(f"  Ready: [yellow]{ready_count}[/yellow]")
        console.print(f"  Processed: [green]{processed_count}[/green]")
        console.print(f"  Failed: [red]{failed_count}[/red]")

        # Show sample processed documents
        if processed_count > 0:
            console.print(f"\n[bold cyan]Sample Chunked Documents (first {limit}):[/bold cyan]\n")

            processed_docs = [s for s in all_status if s.status == ProcessingStatus.PROCESSED][:limit]

            for i, status in enumerate(processed_docs, 1):
                # Check if JSON file exists
                json_path = GOLD_BASE_PATH / status.project_id / f"{status.reference_doc_id}.json"

                console.print(f"[cyan]{i}. Project: {status.project_id[:20]}...[/cyan]")
                console.print(f"   Reference Doc: {status.reference_doc_id}")
                console.print(f"   Status: [green]{status.status.value}[/green]")
                console.print(f"   Chunk Count: {status.chunk_count}")
                console.print(f"   Execution Time: {status.execution_time:.2f}s")
                console.print(f"   JSON Exists: {json_path.exists()}")
                if json_path.exists():
                    console.print(f"   Location: {json_path}")
                console.print()

        # Show failed documents
        if failed_count > 0:
            console.print(f"\n[bold yellow]Failed Documents (first 5):[/bold yellow]\n")

            failed_docs = [s for s in all_status if s.status == ProcessingStatus.FAILED][:5]

            for i, status in enumerate(failed_docs, 1):
                console.print(f"[yellow]{i}. Project: {status.project_id[:20]}...[/yellow]")
                console.print(f"   Error: {status.error_message[:100]}...")
                console.print()


if __name__ == "__main__":
    app()
