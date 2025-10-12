#!/usr/bin/env python3
"""
Tool to load contract data from master_clauses.csv into contract_asmd table.

Usage:
    uv run python src/tools/load_contract_data.py
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import polars as pl
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlmodel import Session, SQLModel, create_engine, select

from contramate.dbs.models.contract import ContractAsmd
from contramate.utils.settings.factory import settings_factory

app = typer.Typer(help="Load contract data into PostgreSQL")
console = Console()

# Base path for contract PDFs
CONTRACTS_BASE_PATH = Path("data/bronze/full_contract_pdf")


def find_contract_type(filename: str) -> Optional[str]:
    """Find contract type by searching for file in directory structure

    The contract type is the subdirectory within Part_I/Part_II/Part_III
    (e.g., "Affiliate_Agreements", "Agency Agreements", etc.)

    Args:
        filename: The filename to search for

    Returns:
        Contract type (subdirectory name) or None if not found
    """
    if not CONTRACTS_BASE_PATH.exists():
        return None

    # Search in each Part directory
    for part in ["Part_I", "Part_II", "Part_III"]:
        part_path = CONTRACTS_BASE_PATH / part
        if not part_path.exists():
            continue

        # Search for the file recursively in this part
        for pdf_file in part_path.rglob(filename):
            # Get the parent directory name (the contract type subdirectory)
            # pdf_file.parent is the immediate parent directory of the PDF
            contract_type_dir = pdf_file.parent.name
            return contract_type_dir

    return None


def normalize_value(value) -> Optional[str]:
    """Normalize values from DataFrame

    Args:
        value: Raw value from DataFrame

    Returns:
        Normalized value or None
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None

    if isinstance(value, str):
        # Remove quotes and brackets from list representations
        cleaned = value.strip().strip("[]").strip("'").strip('"')

        if cleaned.lower() in ["", "no", "none", "null"]:
            return None

        return cleaned

    return str(value)


def map_row_to_model(row: dict) -> ContractAsmd:
    """Map row dictionary to ContractAsmd model

    Args:
        row: Dictionary from polars DataFrame

    Returns:
        ContractAsmd instance
    """
    # Generate unique UUIDs for both primary keys
    filename = row.get("Filename", "")

    # Generate unique project_id per row
    project_id = str(uuid.uuid4())

    # Generate unique reference_doc_id from filename
    reference_doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, filename))

    # Extract contract type from directory structure
    contract_type = find_contract_type(filename)

    now = datetime.now(timezone.utc)

    return ContractAsmd(
        # Primary keys
        project_id=project_id,
        reference_doc_id=reference_doc_id,

        # Core identifiers
        document_title=filename,
        contract_type=contract_type,

        # Document metadata
        document_name=normalize_value(row.get("Document Name")),
        document_name_answer=normalize_value(row.get("Document Name-Answer")),

        # Parties
        parties=normalize_value(row.get("Parties")),
        parties_answer=normalize_value(row.get("Parties-Answer")),

        # Key dates
        agreement_date=normalize_value(row.get("Agreement Date")),
        agreement_date_answer=normalize_value(row.get("Agreement Date-Answer")),
        effective_date=normalize_value(row.get("Effective Date")),
        effective_date_answer=normalize_value(row.get("Effective Date-Answer")),
        expiration_date=normalize_value(row.get("Expiration Date")),
        expiration_date_answer=normalize_value(row.get("Expiration Date-Answer")),

        # Renewal terms
        renewal_term=normalize_value(row.get("Renewal Term")),
        renewal_term_answer=normalize_value(row.get("Renewal Term-Answer")),
        notice_period_to_terminate_renewal=normalize_value(row.get("Notice Period To Terminate Renewal")),
        notice_period_to_terminate_renewal_answer=normalize_value(row.get("Notice Period To Terminate Renewal- Answer")),

        # Legal
        governing_law=normalize_value(row.get("Governing Law")),
        governing_law_answer=normalize_value(row.get("Governing Law-Answer")),

        # Contract clauses
        most_favored_nation=normalize_value(row.get("Most Favored Nation")),
        most_favored_nation_answer=normalize_value(row.get("Most Favored Nation-Answer")),
        competitive_restriction_exception=normalize_value(row.get("Competitive Restriction Exception")),
        competitive_restriction_exception_answer=normalize_value(row.get("Competitive Restriction Exception-Answer")),
        non_compete=normalize_value(row.get("Non-Compete")),
        non_compete_answer=normalize_value(row.get("Non-Compete-Answer")),
        exclusivity=normalize_value(row.get("Exclusivity")),
        exclusivity_answer=normalize_value(row.get("Exclusivity-Answer")),
        no_solicit_of_customers=normalize_value(row.get("No-Solicit Of Customers")),
        no_solicit_of_customers_answer=normalize_value(row.get("No-Solicit Of Customers-Answer")),
        no_solicit_of_employees=normalize_value(row.get("No-Solicit Of Employees")),
        no_solicit_of_employees_answer=normalize_value(row.get("No-Solicit Of Employees-Answer")),
        non_disparagement=normalize_value(row.get("Non-Disparagement")),
        non_disparagement_answer=normalize_value(row.get("Non-Disparagement-Answer")),
        termination_for_convenience=normalize_value(row.get("Termination For Convenience")),
        termination_for_convenience_answer=normalize_value(row.get("Termination For Convenience-Answer")),

        # Rights and ownership
        rofr_rofo_rofn=normalize_value(row.get("Rofr/Rofo/Rofn")),
        rofr_rofo_rofn_answer=normalize_value(row.get("Rofr/Rofo/Rofn-Answer")),
        change_of_control=normalize_value(row.get("Change Of Control")),
        change_of_control_answer=normalize_value(row.get("Change Of Control-Answer")),
        anti_assignment=normalize_value(row.get("Anti-Assignment")),
        anti_assignment_answer=normalize_value(row.get("Anti-Assignment-Answer")),

        # Financial terms
        revenue_profit_sharing=normalize_value(row.get("Revenue/Profit Sharing")),
        revenue_profit_sharing_answer=normalize_value(row.get("Revenue/Profit Sharing-Answer")),
        price_restrictions=normalize_value(row.get("Price Restrictions")),
        price_restrictions_answer=normalize_value(row.get("Price Restrictions-Answer")),
        minimum_commitment=normalize_value(row.get("Minimum Commitment")),
        minimum_commitment_answer=normalize_value(row.get("Minimum Commitment-Answer")),
        volume_restriction=normalize_value(row.get("Volume Restriction")),
        volume_restriction_answer=normalize_value(row.get("Volume Restriction-Answer")),

        # IP and licensing
        ip_ownership_assignment=normalize_value(row.get("Ip Ownership Assignment")),
        ip_ownership_assignment_answer=normalize_value(row.get("Ip Ownership Assignment-Answer")),
        joint_ip_ownership=normalize_value(row.get("Joint Ip Ownership")),
        joint_ip_ownership_answer=normalize_value(row.get("Joint Ip Ownership-Answer")),
        license_grant=normalize_value(row.get("License Grant")),
        license_grant_answer=normalize_value(row.get("License Grant-Answer")),
        non_transferable_license=normalize_value(row.get("Non-Transferable License")),
        non_transferable_license_answer=normalize_value(row.get("Non-Transferable License-Answer")),
        affiliate_license_licensor=normalize_value(row.get("Affiliate License-Licensor")),
        affiliate_license_licensor_answer=normalize_value(row.get("Affiliate License-Licensor-Answer")),
        affiliate_license_licensee=normalize_value(row.get("Affiliate License-Licensee")),
        affiliate_license_licensee_answer=normalize_value(row.get("Affiliate License-Licensee-Answer")),
        unlimited_all_you_can_eat_license=normalize_value(row.get("Unlimited/All-You-Can-Eat-License")),
        unlimited_all_you_can_eat_license_answer=normalize_value(row.get("Unlimited/All-You-Can-Eat-License-Answer")),
        irrevocable_or_perpetual_license=normalize_value(row.get("Irrevocable Or Perpetual License")),
        irrevocable_or_perpetual_license_answer=normalize_value(row.get("Irrevocable Or Perpetual License-Answer")),
        source_code_escrow=normalize_value(row.get("Source Code Escrow")),
        source_code_escrow_answer=normalize_value(row.get("Source Code Escrow-Answer")),
        post_termination_services=normalize_value(row.get("Post-Termination Services")),
        post_termination_services_answer=normalize_value(row.get("Post-Termination Services-Answer")),

        # Liability and warranty
        uncapped_liability=normalize_value(row.get("Uncapped Liability")),
        uncapped_liability_answer=normalize_value(row.get("Uncapped Liability-Answer")),
        cap_on_liability=normalize_value(row.get("Cap On Liability")),
        cap_on_liability_answer=normalize_value(row.get("Cap On Liability-Answer")),
        liquidated_damages=normalize_value(row.get("Liquidated Damages")),
        liquidated_damages_answer=normalize_value(row.get("Liquidated Damages-Answer")),
        warranty_duration=normalize_value(row.get("Warranty Duration")),
        warranty_duration_answer=normalize_value(row.get("Warranty Duration-Answer")),

        # Other provisions
        insurance=normalize_value(row.get("Insurance")),
        insurance_answer=normalize_value(row.get("Insurance-Answer")),
        audit_rights=normalize_value(row.get("Audit Rights")),
        audit_rights_answer=normalize_value(row.get("Audit Rights-Answer")),
        covenant_not_to_sue=normalize_value(row.get("Covenant Not To Sue")),
        covenant_not_to_sue_answer=normalize_value(row.get("Covenant Not To Sue-Answer")),
        third_party_beneficiary=normalize_value(row.get("Third Party Beneficiary")),
        third_party_beneficiary_answer=normalize_value(row.get("Third Party Beneficiary-Answer")),

        # Metadata
        created_at=now,
        updated_at=now,
    )


@app.command()
def load(
    csv_file: Path = typer.Option(
        Path("data/bronze/master_clauses.csv"),
        "--csv",
        "-f",
        help="Path to master_clauses.csv file"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview data without inserting"
    ),
    batch_size: int = typer.Option(
        100,
        "--batch-size",
        "-b",
        help="Number of records to insert per batch"
    )
):
    """Load contract data from CSV into PostgreSQL database"""

    # Validate CSV file exists
    if not csv_file.exists():
        console.print(f"[red]Error: CSV file not found at {csv_file}[/red]")
        raise typer.Exit(1)

    # Create database engine
    postgres_settings = settings_factory.create_postgres_settings()
    connection_string = postgres_settings.connection_string
    engine = create_engine(connection_string, echo=False)

    # Create tables if they don't exist
    console.print("[cyan]Creating database tables if needed...[/cyan]")
    SQLModel.metadata.create_all(engine)

    # Read and process CSV using polars
    console.print(f"[cyan]Reading CSV file: {csv_file}[/cyan]\n")

    # Read CSV with polars
    df = pl.read_csv(csv_file)

    console.print(f"[cyan]Processing {len(df)} rows...[/cyan]\n")

    # Convert to list of dicts
    records = []
    skipped = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Converting rows to models...", total=len(df))

        for row in df.iter_rows(named=True):
            try:
                contract = map_row_to_model(row)
                records.append(contract)
                progress.update(task, advance=1)
            except Exception as e:
                console.print(f"[yellow]Warning: Skipped row due to error: {e}[/yellow]")
                skipped += 1
                progress.update(task, advance=1)

    console.print(f"\n[green]✓ Processed {len(records)} records from CSV[/green]")
    if skipped > 0:
        console.print(f"[yellow]! Skipped {skipped} records due to errors[/yellow]")

    # Dry run - just show sample data
    if dry_run:
        console.print("\n[bold cyan]DRY RUN MODE - Showing sample data (first 3 records):[/bold cyan]\n")
        for i, record in enumerate(records[:3], 1):
            console.print(f"[bold]Record {i}:[/bold]")
            console.print(f"  Project ID: {record.project_id}")
            console.print(f"  Reference Doc ID: {record.reference_doc_id}")
            console.print(f"  Document Title: {record.document_title}")
            console.print(f"  Contract Type: {record.contract_type or 'N/A'}")
            console.print(f"  Parties: {record.parties_answer}")
            console.print(f"  Governing Law: {record.governing_law_answer}")
            console.print()
        return

    # Insert data into database
    console.print("\n[cyan]Inserting data into database...[/cyan]")

    with Session(engine) as session:
        # Check for existing records
        existing_count = session.exec(select(ContractAsmd)).all()

        if existing_count:
            console.print(f"[yellow]Found {len(existing_count)} existing records in contract_asmd table[/yellow]")
            confirm = typer.confirm("Do you want to delete existing records and reload?")
            if confirm:
                for record in existing_count:
                    session.delete(record)
                session.commit()
                console.print("[green]✓ Deleted existing records[/green]")
            else:
                console.print("[yellow]Aborted. Use --dry-run to preview data.[/yellow]")
                return

        # Insert records
        total_inserted = 0
        errors = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Inserting records...", total=len(records))

            for i, record in enumerate(records):
                try:
                    session.add(record)
                    session.commit()  # Commit each record immediately
                    total_inserted += 1
                    progress.update(task, advance=1)

                except Exception as e:
                    session.rollback()
                    error_msg = f"Record {i+1} ({record.document_title}): {str(e)[:100]}"
                    errors.append(error_msg)
                    console.print(f"[yellow]! Skipped: {error_msg}[/yellow]")
                    progress.update(task, advance=1)

        console.print(f"\n[bold green]✓ Successfully inserted {total_inserted} records![/bold green]")

        if errors:
            console.print(f"\n[yellow]! {len(errors)} records skipped due to errors:[/yellow]")
            for error in errors[:10]:  # Show first 10 errors
                console.print(f"  {error}")
            if len(errors) > 10:
                console.print(f"  ... and {len(errors) - 10} more errors")


@app.command()
def verify(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to display")
):
    """Verify loaded data in the database"""

    postgres_settings = settings_factory.create_postgres_settings()
    connection_string = postgres_settings.connection_string
    engine = create_engine(connection_string, echo=False)

    with Session(engine) as session:
        # Count total records
        statement = select(ContractAsmd)
        results = session.exec(statement).all()

        console.print(f"\n[bold cyan]Database Statistics:[/bold cyan]")
        console.print(f"Total records in contract_asmd table: {len(results)}")

        if results:
            console.print(f"\n[bold cyan]Sample Records (showing {min(limit, len(results))}):[/bold cyan]\n")
            for i, record in enumerate(results[:limit], 1):
                console.print(f"[bold]{i}. {record.document_title}[/bold]")
                console.print(f"   Reference Doc ID: {record.reference_doc_id}")
                console.print(f"   Parties: {record.parties_answer or 'N/A'}")
                console.print(f"   Governing Law: {record.governing_law_answer or 'N/A'}")
                console.print(f"   Created: {record.created_at}")
                console.print()


if __name__ == "__main__":
    app()
