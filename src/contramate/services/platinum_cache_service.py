"""
Platinum Cache Service for caching PlatinumModel instances with embeddings.

Caches platinum models (chunks + vectors) as Parquet files to avoid
expensive OpenAI API calls on re-indexing.

Cache location: data/platinum-cached/{project_id}/{reference_doc_id}/{filename}.parquet
"""

import polars as pl
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from loguru import logger

from contramate.models.platinum import PlatinumModel


# Base cache directory
PLATINUM_CACHE_BASE = Path("data/platinum-cached")


def get_cache_path(project_id: str, reference_doc_id: str, filename: str) -> Path:
    """
    Get the cache file path for a platinum document.

    Args:
        project_id: Project identifier
        reference_doc_id: Document identifier
        filename: Original filename (e.g., "Contract.md")

    Returns:
        Path to cached parquet file (e.g., "Contract.md.parquet")
    """
    cache_dir = PLATINUM_CACHE_BASE / project_id / reference_doc_id
    cache_file = cache_dir / f"{filename}.parquet"
    return cache_file


def save_platinum_models_to_cache(
    platinum_models: List[PlatinumModel],
    project_id: str,
    reference_doc_id: str,
    filename: str
) -> Path:
    """
    Save platinum models to Parquet cache.

    Args:
        platinum_models: List of PlatinumModel instances to cache
        project_id: Project identifier
        reference_doc_id: Document identifier
        filename: Original filename

    Returns:
        Path to created cache file
    """
    if not platinum_models:
        raise ValueError("Cannot cache empty list of platinum models")

    # Get cache path and ensure directory exists
    cache_path = get_cache_path(project_id, reference_doc_id, filename)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert platinum models to dictionaries
    records = [model.to_dict() for model in platinum_models]

    # Create Polars DataFrame
    df = pl.DataFrame(records)

    # Save to Parquet with compression
    df.write_parquet(cache_path, compression="zstd", compression_level=3)

    logger.debug(f"Cached {len(platinum_models)} platinum models to {cache_path}")
    return cache_path


def load_platinum_models_from_cache(
    project_id: str,
    reference_doc_id: str,
    filename: str
) -> Optional[List[PlatinumModel]]:
    """
    Load platinum models from Parquet cache.

    Args:
        project_id: Project identifier
        reference_doc_id: Document identifier
        filename: Original filename

    Returns:
        List of PlatinumModel instances or None if cache doesn't exist
    """
    cache_path = get_cache_path(project_id, reference_doc_id, filename)

    if not cache_path.exists():
        return None

    try:
        # Load Parquet file
        df = pl.read_parquet(cache_path)

        # Convert back to PlatinumModel instances
        platinum_models = [
            PlatinumModel.from_dict(row)
            for row in df.to_dicts()
        ]

        logger.debug(f"Loaded {len(platinum_models)} platinum models from cache: {cache_path}")
        return platinum_models

    except Exception as e:
        logger.warning(f"Failed to load cache from {cache_path}: {e}")
        return None


def is_cache_valid(
    project_id: str,
    reference_doc_id: str,
    filename: str,
    gold_file_path: Path
) -> bool:
    """
    Check if cached platinum file exists and is newer than gold file.

    Args:
        project_id: Project identifier
        reference_doc_id: Document identifier
        filename: Original filename
        gold_file_path: Path to gold layer JSON file

    Returns:
        True if cache exists and is valid (newer than gold file)
    """
    cache_path = get_cache_path(project_id, reference_doc_id, filename)

    # Cache doesn't exist
    if not cache_path.exists():
        logger.debug(f"Cache does not exist: {cache_path}")
        return False

    # Gold file doesn't exist (shouldn't happen, but handle it)
    if not gold_file_path.exists():
        logger.warning(f"Gold file does not exist: {gold_file_path}")
        return False

    # Compare modification times
    cache_mtime = cache_path.stat().st_mtime
    gold_mtime = gold_file_path.stat().st_mtime

    is_valid = cache_mtime >= gold_mtime

    if is_valid:
        logger.debug(f"Cache is valid: {cache_path}")
    else:
        cache_time = datetime.fromtimestamp(cache_mtime)
        gold_time = datetime.fromtimestamp(gold_mtime)
        logger.debug(
            f"Cache is stale: cache={cache_time}, gold={gold_time}"
        )

    return is_valid


def clear_cache(project_id: Optional[str] = None, reference_doc_id: Optional[str] = None) -> int:
    """
    Clear platinum cache files.

    Args:
        project_id: If provided, only clear cache for this project
        reference_doc_id: If provided (with project_id), only clear cache for this document

    Returns:
        Number of files deleted
    """
    deleted_count = 0

    if project_id and reference_doc_id:
        # Clear specific document
        cache_dir = PLATINUM_CACHE_BASE / project_id / reference_doc_id
        if cache_dir.exists():
            for cache_file in cache_dir.glob("*.parquet"):
                cache_file.unlink()
                deleted_count += 1
            # Remove empty directory
            if not any(cache_dir.iterdir()):
                cache_dir.rmdir()
    elif project_id:
        # Clear entire project
        project_dir = PLATINUM_CACHE_BASE / project_id
        if project_dir.exists():
            for cache_file in project_dir.rglob("*.parquet"):
                cache_file.unlink()
                deleted_count += 1
            # Remove empty directories
            for dir_path in sorted(project_dir.rglob("*"), reverse=True):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
    else:
        # Clear all cache
        if PLATINUM_CACHE_BASE.exists():
            for cache_file in PLATINUM_CACHE_BASE.rglob("*.parquet"):
                cache_file.unlink()
                deleted_count += 1
            # Remove empty directories
            for dir_path in sorted(PLATINUM_CACHE_BASE.rglob("*"), reverse=True):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    dir_path.rmdir()

    logger.info(f"Cleared {deleted_count} cached platinum files")
    return deleted_count
