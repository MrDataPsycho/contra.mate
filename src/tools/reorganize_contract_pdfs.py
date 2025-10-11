#!/usr/bin/env python3
"""
Tool to reorganize contract PDFs based on database structure.

Reads contract_asmd table and reorganizes PDFs into:
data/bronze-v2/{project_id}/{reference_doc_id}/{filename}

Usage:
    uv run python src/tools/reorganize_contract_pdfs.py
"""

import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlmodel import Session, create_engine, select

from contramate.dbs.models.contract import ContractAsmd
from contramate.utils.settings.core import settings

app = typer.Typer(help="Reorganize contract PDFs based on database structure")
console = Console()

# Paths
SOURCE_BASE_PATH = Path("data/bronze/full_contract_pdf")
TARGET_BASE_PATH = Path("data/bronze-v2")


def find_pdf_file(filename: str) -> Optional[Path]:
    """Find PDF file in source directory structure (case-insensitive)

    Args:
        filename: The filename to search for

    Returns:
        Full path to the PDF file or None if not found
    """
    if not SOURCE_BASE_PATH.exists():
        return None

    # Search recursively for the file (case-insensitive)
    filename_lower = filename.lower()
    for pdf_file in SOURCE_BASE_PATH.rglob("*"):
        if pdf_file.is_file() and pdf_file.name.lower() == filename_lower:
            return pdf_file

    return None


@app.command()
def reorganize(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview operations without copying files"
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing files in target directory"
    )
):
    """Reorganize contract PDFs into project_id/reference_doc_id structure"""

    # Create database connection
    connection_string = settings.postgres.connection_string
    engine = create_engine(connection_string, echo=False)

    # Statistics
    total_records = 0
    found_files = 0
    not_found_files = 0
    copied_files = 0
    skipped_files = 0

    not_found_list = []

    console.print(f"[cyan]Source directory: {SOURCE_BASE_PATH}[/cyan]")
    console.print(f"[cyan]Target directory: {TARGET_BASE_PATH}[/cyan]\n")

    if dry_run:
        console.print("[bold yellow]DRY RUN MODE - No files will be copied[/bold yellow]\n")

    with Session(engine) as session:
        # Get all records
        statement = select(ContractAsmd)
        records = session.exec(statement).all()
        total_records = len(records)

        console.print(f"[cyan]Processing {total_records} contract records...[/cyan]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing contracts...", total=total_records)

            for record in records:
                # Find the PDF file
                pdf_path = find_pdf_file(record.document_title)

                if not pdf_path:
                    not_found_files += 1
                    not_found_list.append(record.document_title)
                    progress.update(task, advance=1)
                    continue

                found_files += 1

                # Create target directory structure
                target_dir = TARGET_BASE_PATH / record.project_id / record.reference_doc_id
                target_file = target_dir / record.document_title

                # Check if file already exists
                if target_file.exists() and not overwrite:
                    skipped_files += 1
                    progress.update(task, advance=1)
                    continue

                if not dry_run:
                    # Create target directory
                    target_dir.mkdir(parents=True, exist_ok=True)

                    # Copy the file
                    try:
                        shutil.copy2(pdf_path, target_file)
                        copied_files += 1
                    except Exception as e:
                        console.print(f"[red]Error copying {record.document_title}: {e}[/red]")

                else:
                    copied_files += 1  # Count as copied for dry run

                progress.update(task, advance=1)

    # Print summary
    console.print("\n[bold cyan]Summary:[/bold cyan]")
    console.print(f"  Total records: {total_records}")
    console.print(f"  Files found: {found_files}")
    console.print(f"  Files not found: {not_found_files}")
    console.print(f"  Files copied: {copied_files}")
    console.print(f"  Files skipped (already exist): {skipped_files}")

    if not_found_list:
        console.print(f"\n[yellow]Files not found (first 10):[/yellow]")
        for filename in not_found_list[:10]:
            console.print(f"  - {filename}")
        if len(not_found_list) > 10:
            console.print(f"  ... and {len(not_found_list) - 10} more")

    if dry_run:
        console.print("\n[yellow]This was a dry run. Use without --dry-run to actually copy files.[/yellow]")
    else:
        console.print(f"\n[bold green]✓ Files reorganized successfully![/bold green]")
        console.print(f"[dim]Target directory: {TARGET_BASE_PATH}[/dim]")


@app.command()
def verify(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of directories to check")
):
    """Verify reorganized directory structure"""

    if not TARGET_BASE_PATH.exists():
        console.print(f"[red]Target directory does not exist: {TARGET_BASE_PATH}[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Checking directory structure in {TARGET_BASE_PATH}...[/cyan]\n")

    # Count directories and files
    project_dirs = [d for d in TARGET_BASE_PATH.iterdir() if d.is_dir()]
    total_projects = len(project_dirs)
    # Count both .pdf and .PDF extensions
    total_files = sum(1 for _ in TARGET_BASE_PATH.rglob("*.pdf")) + sum(1 for _ in TARGET_BASE_PATH.rglob("*.PDF"))

    console.print(f"[bold]Statistics:[/bold]")
    console.print(f"  Project directories: {total_projects}")
    console.print(f"  Total PDF files: {total_files}")

    console.print(f"\n[bold]Sample structure (first {min(limit, total_projects)} projects):[/bold]\n")

    for i, project_dir in enumerate(project_dirs[:limit], 1):
        console.print(f"[cyan]{i}. Project: {project_dir.name}[/cyan]")

        # List reference doc directories
        ref_dirs = [d for d in project_dir.iterdir() if d.is_dir()]
        for ref_dir in ref_dirs[:3]:  # Show first 3 reference docs per project
            pdfs = list(ref_dir.glob("*.pdf"))
            console.print(f"   └── {ref_dir.name}/ ({len(pdfs)} PDF{'s' if len(pdfs) != 1 else ''})")
            for pdf in pdfs[:2]:  # Show first 2 PDFs
                console.print(f"       └── {pdf.name}")

        if len(ref_dirs) > 3:
            console.print(f"   └── ... and {len(ref_dirs) - 3} more reference docs")
        console.print()


if __name__ == "__main__":
    app()
