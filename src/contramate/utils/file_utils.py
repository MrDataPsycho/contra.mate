"""File utility functions for reading and writing files."""

from pathlib import Path
from typing import Optional
from loguru import logger


def read_markdown(file_path: str | Path) -> Optional[str]:
    """Read markdown content from a file.

    Args:
        file_path: Path to the markdown file (can be string or Path object)

    Returns:
        str: Content of the markdown file
        None: If file doesn't exist or error occurs

    Raises:
        FileNotFoundError: If the file doesn't exist
        IOError: If there's an error reading the file
    """
    path = Path(file_path)

    if not path.exists():
        logger.error(f"File not found: {path}")
        raise FileNotFoundError(f"Markdown file not found: {path}")

    if not path.is_file():
        logger.error(f"Path is not a file: {path}")
        raise ValueError(f"Path is not a file: {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        logger.info(f"Successfully read markdown file: {path} ({len(content)} chars)")
        return content

    except Exception as e:
        logger.error(f"Error reading markdown file {path}: {e}")
        raise IOError(f"Failed to read markdown file {path}: {e}") from e


def read_markdown_safe(file_path: str | Path) -> Optional[str]:
    """Read markdown content from a file with error handling.

    This is a safe version that returns None instead of raising exceptions.

    Args:
        file_path: Path to the markdown file (can be string or Path object)

    Returns:
        str: Content of the markdown file
        None: If file doesn't exist or error occurs
    """
    try:
        return read_markdown(file_path)
    except Exception as e:
        logger.warning(f"Could not read markdown file {file_path}: {e}")
        return None
