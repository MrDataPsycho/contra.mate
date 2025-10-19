#!/usr/bin/env python3
"""
Fix cached platinum models to ensure chunk_id matches chunk_index.

This script:
1. Loads all cached platinum models
2. Updates chunk_id to match chunk_index (removes +1 offset)
3. Updates display_name to use the corrected chunk_id
4. Saves the corrected models back to cache

Usage:
    uv run python src/tools/fix_platinum_cache.py --dry-run
    uv run python src/tools/fix_platinum_cache.py --fix
"""

from pathlib import Path
from typing import List
import typer
from loguru import logger

from contramate.models.platinum import PlatinumModel
from contramate.services import platinum_cache_service

app = typer.Typer()

PLATINUM_CACHE_PATH = Path("data/platinum-cached")


def get_all_cached_platinum_files() -> List[Path]:
    """Find all cached platinum Parquet files."""
    if not PLATINUM_CACHE_PATH.exists():
        logger.warning(f"Platinum cache directory does not exist: {PLATINUM_CACHE_PATH}")
        return []

    # Pattern: data/platinum-cached/{project_id}/{reference_doc_id}/{filename}.parquet
    parquet_files = list(PLATINUM_CACHE_PATH.glob("*/*/*.parquet"))
    return parquet_files


def fix_platinum_models(platinum_models: List[PlatinumModel]) -> tuple[List[PlatinumModel], int]:
    """
    Fix platinum models by ensuring chunk_id matches chunk_index.

    Returns:
        Tuple of (fixed_models, num_fixed)
    """
    fixed_models = []
    num_fixed = 0

    for model in platinum_models:
        needs_fix = model.chunk_id != model.chunk_index

        if needs_fix:
            # Create corrected model
            corrected_model = model.model_copy(
                update={
                    "chunk_id": model.chunk_index,
                    # Update display_name to use corrected chunk_id
                    "display_name": f"{model.document_title}-{model.chunk_index}"
                }
            )
            fixed_models.append(corrected_model)
            num_fixed += 1

            logger.debug(
                f"Fixed: chunk_id {model.chunk_id} -> {corrected_model.chunk_id}, "
                f"display_name: {model.display_name} -> {corrected_model.display_name}"
            )
        else:
            # No change needed
            fixed_models.append(model)

    return fixed_models, num_fixed


@app.command()
def fix(
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--fix",
        help="Dry run mode (preview changes) or actually fix and save"
    )
):
    """Fix cached platinum models to ensure chunk_id matches chunk_index."""

    logger.info("=" * 70)
    logger.info("Platinum Cache Fixer")
    logger.info("=" * 70)
    logger.info(f"Mode: {'DRY RUN (no changes will be saved)' if dry_run else 'FIX (changes will be saved)'}")
    logger.info(f"Cache directory: {PLATINUM_CACHE_PATH}")
    logger.info("")

    # Find all cached files
    cached_files = get_all_cached_platinum_files()

    if not cached_files:
        logger.info("No cached platinum files found!")
        return

    logger.info(f"Found {len(cached_files)} cached platinum files\n")

    total_models_processed = 0
    total_models_fixed = 0
    files_with_fixes = 0

    for cache_file in cached_files:
        # Extract project_id, reference_doc_id, filename from path
        # Path format: data/platinum-cached/{project_id}/{reference_doc_id}/{filename}.parquet
        parts = cache_file.parts
        project_id = parts[-3]
        reference_doc_id = parts[-2]
        filename = cache_file.stem  # Remove .parquet extension

        logger.info(f"Processing: {project_id}/{reference_doc_id}/{filename}")

        # Load platinum models from cache
        platinum_models = platinum_cache_service.load_platinum_models_from_cache(
            project_id=project_id,
            reference_doc_id=reference_doc_id,
            filename=filename
        )

        if not platinum_models:
            logger.warning(f"  ⚠ Could not load models from {cache_file}")
            continue

        logger.info(f"  Loaded {len(platinum_models)} platinum models")
        total_models_processed += len(platinum_models)

        # Fix the models
        fixed_models, num_fixed = fix_platinum_models(platinum_models)

        if num_fixed > 0:
            logger.info(f"  ✓ Fixed {num_fixed} models")
            files_with_fixes += 1
            total_models_fixed += num_fixed

            # Show sample of changes
            for i, (original, fixed) in enumerate(zip(platinum_models, fixed_models)):
                if original.chunk_id != fixed.chunk_id:
                    logger.info(
                        f"    Chunk {i}: chunk_id {original.chunk_id} -> {fixed.chunk_id}, "
                        f"record_id {original.record_id} -> {fixed.record_id}"
                    )
                    if i >= 2:  # Show max 3 examples
                        logger.info(f"    ... and {num_fixed - 3} more")
                        break

            # Save back to cache (if not dry-run)
            if not dry_run:
                try:
                    platinum_cache_service.save_platinum_models_to_cache(
                        platinum_models=fixed_models,
                        project_id=project_id,
                        reference_doc_id=reference_doc_id,
                        filename=filename
                    )
                    logger.info(f"  ✓ Saved corrected models to cache")
                except Exception as e:
                    logger.error(f"  ✗ Failed to save: {e}")
        else:
            logger.info(f"  ✓ No fixes needed (all models already correct)")

        logger.info("")

    # Summary
    logger.info("=" * 70)
    logger.info("Summary")
    logger.info("=" * 70)
    logger.info(f"Total cached files: {len(cached_files)}")
    logger.info(f"Files with fixes: {files_with_fixes}")
    logger.info(f"Total models processed: {total_models_processed}")
    logger.info(f"Total models fixed: {total_models_fixed}")

    if dry_run:
        logger.info("")
        logger.info("⚠ DRY RUN MODE - No changes were saved!")
        logger.info("Run with --fix to apply changes:")
        logger.info("  uv run python src/tools/fix_platinum_cache.py --fix")
    else:
        logger.info("")
        logger.info("✓ Changes have been saved to cache!")
        logger.info("You can now re-index to OpenSearch without regenerating embeddings:")
        logger.info("  uv run python src/tools/gold_to_platinum.py index --limit 10")


if __name__ == "__main__":
    app()
