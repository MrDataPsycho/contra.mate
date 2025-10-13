#!/usr/bin/env python3
"""
Tool to convert contract PDFs to markdown using pymupdf4llm.

Converts PDFs from bronze-v2 layer to markdown in silver layer.
Tracks conversion status in document_conversion_status table.

Usage:
    uv run python src/tools/pdf_to_markdown.py convert
    uv run python src/tools/pdf_to_markdown.py convert --limit 10
    uv run python src/tools/pdf_to_markdown.py verify
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pymupdf
import pymupdf4llm
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlmodel import Session, create_engine, select

from contramate.dbs.models.contract import ContractAsmd
from contramate.dbs.models.document_status import (
    DocumentConversionStatus,
    ProcessingStatus,
)
from contramate.utils.settings.factory import settings_factory

app = typer.Typer(help="Convert contract PDFs to markdown")
console = Console()

# Paths
BRONZE_BASE_PATH = Path("data/bronze-v2")
SILVER_BASE_PATH = Path("data/silver")


def find_file_in_bronze(project_id: str, reference_doc_id: str) -> Optional[Path]:
    """Find any file in bronze directory structure

    Args:
        project_id: Project identifier
        reference_doc_id: Reference document identifier

    Returns:
        Path to first file found (we'll try to convert it) or None if directory doesn't exist
    """
    doc_dir = BRONZE_BASE_PATH / project_id / reference_doc_id
    if not doc_dir.exists():
        return None

    # Return the first file found (ignore directories)
    for file in doc_dir.iterdir():
        if file.is_file():
            return file

    return None


def convert_pdf_to_markdown(pdf_path: Path) -> str:
    """Convert PDF to markdown using pymupdf4llm with fallback to plain PyMuPDF

    Args:
        pdf_path: Path to PDF file

    Returns:
        Markdown content as string

    Raises:
        RuntimeError: If both pymupdf4llm and fallback extraction fail
    """
    # Try pymupdf4llm first
    markdown_text = pymupdf4llm.to_markdown(str(pdf_path))

    # If pymupdf4llm produces empty output, fallback to plain PyMuPDF extraction
    if not markdown_text or len(markdown_text.strip()) == 0:
        console.print(f"[yellow]⚠ pymupdf4llm produced empty output, using PyMuPDF fallback[/yellow]")

        try:
            doc = pymupdf.open(pdf_path)
            markdown_text = ""

            for page_num, page in enumerate(doc, 1):
                # Extract text from page
                text = page.get_text()

                # Add page separator and content
                if text.strip():
                    markdown_text += f"\n\n---\n\n# Page {page_num}\n\n{text}\n"

            doc.close()

            if not markdown_text or len(markdown_text.strip()) == 0:
                raise RuntimeError("Both pymupdf4llm and PyMuPDF fallback produced empty output")

        except Exception as e:
            raise RuntimeError(f"Fallback extraction failed: {str(e)}")

    return markdown_text


def save_markdown(
    markdown_content: str,
    project_id: str,
    reference_doc_id: str,
    original_filename: str
) -> Path:
    """Save markdown content to silver directory

    Args:
        markdown_content: Markdown text to save
        project_id: Project identifier
        reference_doc_id: Reference document identifier
        original_filename: Original PDF filename

    Returns:
        Path to saved markdown file
    """
    # Create silver directory structure
    silver_dir = SILVER_BASE_PATH / project_id / reference_doc_id
    silver_dir.mkdir(parents=True, exist_ok=True)

    # Append .md to original filename (e.g., contract.pdf -> contract.pdf.md)
    md_filename = original_filename + ".md"
    md_path = silver_dir / md_filename

    # Write markdown content
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    return md_path


@app.command()
def convert(
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
    )
):
    """Convert PDFs to markdown with status tracking"""

    # Create database connection
    postgres_settings = settings_factory.create_postgres_settings()
    connection_string = postgres_settings.connection_string
    engine = create_engine(connection_string, echo=False)

    # Statistics
    total_documents = 0
    processed = 0
    failed = 0
    skipped = 0
    not_found = 0

    console.print(f"[cyan]Starting PDF to Markdown conversion...[/cyan]")
    console.print(f"[cyan]Source: {BRONZE_BASE_PATH}[/cyan]")
    console.print(f"[cyan]Target: {SILVER_BASE_PATH}[/cyan]\n")

    with Session(engine) as session:
        # Get all documents from contract_asmd
        statement = select(ContractAsmd)
        if limit:
            statement = statement.limit(limit)

        contracts = session.exec(statement).all()
        total_documents = len(contracts)

        console.print(f"[cyan]Found {total_documents} documents to process[/cyan]\n")

        # Counter for progress reporting every 10 documents
        doc_counter = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Converting PDFs...", total=total_documents)

            for contract in contracts:
                doc_counter += 1
                project_id = contract.project_id
                reference_doc_id = contract.reference_doc_id

                # Check if already processed
                if skip_existing:
                    existing_status = session.exec(
                        select(DocumentConversionStatus).where(
                            DocumentConversionStatus.project_id == project_id,
                            DocumentConversionStatus.reference_doc_id == reference_doc_id,
                            DocumentConversionStatus.status == ProcessingStatus.PROCESSED
                        )
                    ).first()

                    if existing_status:
                        skipped += 1
                        progress.update(task, advance=1)
                        continue

                # Find file in bronze directory
                file_path = find_file_in_bronze(project_id, reference_doc_id)
                if not file_path:
                    not_found += 1
                    progress.update(task, advance=1)
                    continue

                # Initialize status record
                status_record = DocumentConversionStatus(
                    project_id=project_id,
                    reference_doc_id=reference_doc_id,
                    status=ProcessingStatus.READY,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )

                # Check if status record already exists
                existing = session.exec(
                    select(DocumentConversionStatus).where(
                        DocumentConversionStatus.project_id == project_id,
                        DocumentConversionStatus.reference_doc_id == reference_doc_id
                    )
                ).first()

                if existing:
                    status_record = existing
                    status_record.status = ProcessingStatus.READY
                    status_record.updated_at = datetime.now(timezone.utc)
                else:
                    session.add(status_record)

                session.commit()

                # Convert file to markdown (try any file, handle failures in status)
                start_time = time.time()
                try:
                    markdown_content = convert_pdf_to_markdown(file_path)
                    md_path = save_markdown(
                        markdown_content,
                        project_id,
                        reference_doc_id,
                        file_path.name
                    )

                    execution_time = time.time() - start_time

                    # Update status to PROCESSED
                    status_record.status = ProcessingStatus.PROCESSED
                    status_record.execution_time = execution_time
                    status_record.updated_at = datetime.now(timezone.utc)
                    session.add(status_record)
                    session.commit()

                    processed += 1

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
                    console.print(f"[red]✗ Failed: {contract.document_title[:60]}...[/red]")

                progress.update(task, advance=1)

                # Print progress every 10 documents
                if doc_counter % 10 == 0:
                    progress.stop()
                    console.print(f"\n[bold cyan]Progress Update:[/bold cyan]")
                    console.print(f"  Processed: {doc_counter}/{total_documents} documents")
                    console.print(f"  Success: [green]{processed}[/green] | Failed: [red]{failed}[/red] | Skipped: [yellow]{skipped}[/yellow] | Not Found: [yellow]{not_found}[/yellow]\n")
                    progress.start()

    # Print summary
    console.print("\n[bold cyan]Conversion Summary:[/bold cyan]")
    console.print(f"  Total documents: {total_documents}")
    console.print(f"  Successfully processed: [green]{processed}[/green]")
    console.print(f"  Failed: [red]{failed}[/red]")
    console.print(f"  Skipped (already processed): [yellow]{skipped}[/yellow]")
    console.print(f"  Files not found: [yellow]{not_found}[/yellow]")

    console.print(f"\n[bold green]✓ Conversion complete![/bold green]")
    console.print(f"[dim]Markdown files saved to: {SILVER_BASE_PATH}[/dim]")


@app.command()
def verify(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to show")
):
    """Verify conversion status and show sample markdown files"""

    postgres_settings = settings_factory.create_postgres_settings()
    connection_string = postgres_settings.connection_string
    engine = create_engine(connection_string, echo=False)

    with Session(engine) as session:
        # Get status statistics
        statement = select(DocumentConversionStatus)
        all_status = session.exec(statement).all()

        ready_count = sum(1 for s in all_status if s.status == ProcessingStatus.READY)
        processed_count = sum(1 for s in all_status if s.status == ProcessingStatus.PROCESSED)
        failed_count = sum(1 for s in all_status if s.status == ProcessingStatus.FAILED)

        console.print("[bold cyan]Conversion Status Summary:[/bold cyan]")
        console.print(f"  Total tracked: {len(all_status)}")
        console.print(f"  Ready: [yellow]{ready_count}[/yellow]")
        console.print(f"  Processed: [green]{processed_count}[/green]")
        console.print(f"  Failed: [red]{failed_count}[/red]")

        # Show sample processed documents
        if processed_count > 0:
            console.print(f"\n[bold cyan]Sample Processed Documents (first {limit}):[/bold cyan]\n")

            processed_docs = [s for s in all_status if s.status == ProcessingStatus.PROCESSED][:limit]

            for i, status in enumerate(processed_docs, 1):
                # Check if markdown file exists
                md_dir = SILVER_BASE_PATH / status.project_id / status.reference_doc_id
                md_files = list(md_dir.glob("*.md")) if md_dir.exists() else []

                console.print(f"[cyan]{i}. Project: {status.project_id[:20]}...[/cyan]")
                console.print(f"   Reference Doc: {status.reference_doc_id}")
                console.print(f"   Status: [green]{status.status.value}[/green]")
                console.print(f"   Execution Time: {status.execution_time:.2f}s")
                console.print(f"   Markdown Files: {len(md_files)}")
                if md_files:
                    console.print(f"   Location: {md_files[0]}")
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
