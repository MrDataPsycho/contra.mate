#!/usr/bin/env python3
"""
Tool to extract contract metadata from markdown files using MetadataExtractionService.

Reads markdown files from silver layer, extracts metadata using LLM agent,
and inserts into contract_esmd table.

Tracks extraction status in document_metadata_extraction_status table.

Usage:
    uv run python src/tools/extract_metadata.py extract
    uv run python src/tools/extract_metadata.py extract --limit 10
    uv run python src/tools/extract_metadata.py verify
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlmodel import Session, create_engine, select

from contramate.dbs.models.contract import ContractAsmd, ContractEsmd
from contramate.dbs.models.document_status import (
    DocumentMetadataExtractionStatus,
    ProcessingStatus,
)
from contramate.services.metadata_extraction_service import (
    MetadataExtractionServiceFactory,
)
from contramate.utils.settings.factory import settings_factory

app = typer.Typer(help="Extract contract metadata from markdown files")
console = Console()

# Paths
SILVER_BASE_PATH = Path("data/silver")


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


@app.command()
def extract(
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
    delay_seconds: float = typer.Option(
        1.0,
        "--delay",
        "-d",
        help="Delay in seconds between processing each document (to manage API rate limits)"
    )
):
    """Extract metadata from markdown documents with status tracking"""

    # Create database connection
    postgres_settings = settings_factory.create_postgres_settings()
    connection_string = postgres_settings.connection_string
    engine = create_engine(connection_string, echo=False)

    # Initialize metadata extraction service
    console.print("[cyan]Initializing metadata extraction service...[/cyan]")
    try:
        metadata_service = MetadataExtractionServiceFactory.create_default()
        console.print("[green]✓ Service initialized[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize service: {e}[/red]")
        raise typer.Exit(1)

    # Statistics
    total_documents = 0
    processed = 0
    failed = 0
    skipped = 0
    not_found = 0
    failed_details = []  # Track failed documents with details

    console.print(f"[cyan]Starting metadata extraction...[/cyan]")
    console.print(f"[cyan]Source: {SILVER_BASE_PATH}[/cyan]")
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

        # Pre-check: Count how many will be skipped
        already_processed_count = 0
        if skip_existing:
            for contract in contracts:
                existing_status = session.exec(
                    select(DocumentMetadataExtractionStatus)
                    .where(DocumentMetadataExtractionStatus.project_id == contract.project_id)
                    .where(DocumentMetadataExtractionStatus.reference_doc_id == contract.reference_doc_id)
                    .where(DocumentMetadataExtractionStatus.status == ProcessingStatus.PROCESSED)
                ).first()
                if existing_status:
                    already_processed_count += 1

        to_process_count = total_documents - already_processed_count

        console.print(f"[cyan]Found {total_documents} total documents[/cyan]")
        if skip_existing and already_processed_count > 0:
            console.print(f"[yellow]  - {already_processed_count} already processed (will skip)[/yellow]")
            console.print(f"[green]  - {to_process_count} to process[/green]")
        console.print()

        # Counter for progress reporting
        doc_counter = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Extracting metadata...", total=total_documents)

            for contract in contracts:
                doc_counter += 1
                project_id = contract.project_id
                reference_doc_id = contract.reference_doc_id

                # Check if already processed
                if skip_existing:
                    existing_status = session.exec(
                        select(DocumentMetadataExtractionStatus)
                        .where(DocumentMetadataExtractionStatus.project_id == project_id)
                        .where(DocumentMetadataExtractionStatus.reference_doc_id == reference_doc_id)
                        .where(DocumentMetadataExtractionStatus.status == ProcessingStatus.PROCESSED)
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
                status_record = DocumentMetadataExtractionStatus(
                    project_id=project_id,
                    reference_doc_id=reference_doc_id,
                    status=ProcessingStatus.READY,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )

                # Check if status record already exists
                existing = session.exec(
                    select(DocumentMetadataExtractionStatus).where(
                        DocumentMetadataExtractionStatus.project_id == project_id,
                        DocumentMetadataExtractionStatus.reference_doc_id == reference_doc_id
                    )
                ).first()

                if existing:
                    status_record = existing
                    status_record.status = ProcessingStatus.READY
                    status_record.updated_at = datetime.now(timezone.utc)
                else:
                    session.add(status_record)

                session.commit()

                # Extract metadata from markdown document
                start_time = time.time()
                try:
                    # Step 1: Read markdown content
                    with open(md_file, 'r', encoding='utf-8') as f:
                        markdown_content = f.read()

                    # Step 2: Extract metadata using service
                    metadata_result = metadata_service.execute(
                        text=markdown_content,
                        project_id=project_id,
                        reference_doc_id=reference_doc_id,
                        file_name=md_file.name
                    )

                    if metadata_result.is_err():
                        raise RuntimeError(f"Metadata extraction failed: {metadata_result.unwrap_err()}")

                    contract_esmd = metadata_result.unwrap()

                    # Step 3: Insert into contract_esmd table (upsert)
                    # Check if record already exists
                    existing_esmd = session.exec(
                        select(ContractEsmd).where(
                            ContractEsmd.project_id == project_id,
                            ContractEsmd.reference_doc_id == reference_doc_id
                        )
                    ).first()

                    if existing_esmd:
                        # Update existing record
                        for key, value in contract_esmd.model_dump(exclude_unset=True).items():
                            setattr(existing_esmd, key, value)
                        session.add(existing_esmd)
                    else:
                        # Insert new record
                        session.add(contract_esmd)

                    session.commit()

                    execution_time = time.time() - start_time

                    # Update status to PROCESSED
                    status_record.status = ProcessingStatus.PROCESSED
                    status_record.execution_time = execution_time
                    status_record.updated_at = datetime.now(timezone.utc)
                    session.add(status_record)
                    session.commit()

                    processed += 1

                    # Add delay after successful processing to manage API rate limits
                    if delay_seconds > 0:
                        time.sleep(delay_seconds)

                except Exception as e:
                    # Rollback transaction on error
                    session.rollback()

                    execution_time = time.time() - start_time

                    # Update status to FAILED
                    try:
                        status_record.status = ProcessingStatus.FAILED
                        status_record.execution_time = execution_time
                        status_record.error_message = str(e)[:1000]
                        status_record.updated_at = datetime.now(timezone.utc)
                        session.add(status_record)
                        session.commit()
                    except Exception as commit_error:
                        # If commit fails, rollback again
                        session.rollback()
                        console.print(f"[yellow]⚠ Failed to update status: {commit_error}[/yellow]")

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
    console.print("\n[bold cyan]Extraction Summary:[/bold cyan]")
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

    console.print(f"\n[bold green]✓ Metadata extraction complete![/bold green]")


@app.command()
def verify(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to show")
):
    """Verify extraction status and show sample extracted metadata"""

    postgres_settings = settings_factory.create_postgres_settings()
    connection_string = postgres_settings.connection_string
    engine = create_engine(connection_string, echo=False)

    with Session(engine) as session:
        # Get status statistics
        statement = select(DocumentMetadataExtractionStatus)
        all_status = session.exec(statement).all()

        ready_count = sum(1 for s in all_status if s.status == ProcessingStatus.READY)
        processed_count = sum(1 for s in all_status if s.status == ProcessingStatus.PROCESSED)
        failed_count = sum(1 for s in all_status if s.status == ProcessingStatus.FAILED)

        console.print("[bold cyan]Metadata Extraction Status Summary:[/bold cyan]")
        console.print(f"  Total tracked: {len(all_status)}")
        console.print(f"  Ready: [yellow]{ready_count}[/yellow]")
        console.print(f"  Processed: [green]{processed_count}[/green]")
        console.print(f"  Failed: [red]{failed_count}[/red]")

        # Show sample processed documents
        if processed_count > 0:
            console.print(f"\n[bold cyan]Sample Extracted Metadata (first {limit}):[/bold cyan]\n")

            processed_docs = [s for s in all_status if s.status == ProcessingStatus.PROCESSED][:limit]

            for i, status in enumerate(processed_docs, 1):
                # Get the extracted metadata
                esmd = session.exec(
                    select(ContractEsmd).where(
                        ContractEsmd.project_id == status.project_id,
                        ContractEsmd.reference_doc_id == status.reference_doc_id
                    )
                ).first()

                console.print(f"[cyan]{i}. Project: {status.project_id[:20]}...[/cyan]")
                console.print(f"   Reference Doc: {status.reference_doc_id}")
                console.print(f"   Status: [green]{status.status.value}[/green]")
                console.print(f"   Execution Time: {status.execution_time:.2f}s")

                if esmd:
                    populated_fields = len([v for v in esmd.model_dump(exclude_none=True).values() if v])
                    console.print(f"   Populated Fields: {populated_fields}")
                    console.print(f"   Title: {esmd.title[:60] if esmd.title else 'N/A'}...")
                    console.print(f"   Contract Type: {esmd.contract_type or 'N/A'}")
                    console.print(f"   Total Contract Value: {esmd.total_contract_value or 'N/A'}")
                else:
                    console.print(f"   [yellow]No metadata record found in contract_esmd[/yellow]")

                console.print()

        # Show failed documents
        if failed_count > 0:
            console.print(f"\n[bold yellow]Failed Documents (first 5):[/bold yellow]\n")

            failed_docs = [s for s in all_status if s.status == ProcessingStatus.FAILED][:5]

            for i, status in enumerate(failed_docs, 1):
                console.print(f"[yellow]{i}. Project: {status.project_id[:20]}...[/yellow]")
                console.print(f"   Reference Doc: {status.reference_doc_id}")
                console.print(f"   Error: {status.error_message[:100] if status.error_message else 'Unknown'}...")
                console.print()


if __name__ == "__main__":
    app()
