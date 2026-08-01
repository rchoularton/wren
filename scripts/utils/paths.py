"""
Path utilities for the research assistant scripts.

This module provides portable path handling so scripts work for any user,
on any machine, by deriving the project root from this file's location.

Usage:
    from scripts.utils.paths import PROJECT_ROOT, OUTPUTS_DIR, get_output_path

    # Get path to output directory
    output_dir = get_output_path('crisis_episodes')

    # Ensure directory exists
    ensure_output_dir('my_analysis')
"""

import os
from pathlib import Path

# Calculate PROJECT_ROOT relative to this file
# This file is at: scripts/utils/paths.py
# Project root is: ../../
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Common directories
OUTPUTS_DIR = PROJECT_ROOT / 'outputs'
DATA_DIR = PROJECT_ROOT / 'data'
SCRIPTS_DIR = PROJECT_ROOT / 'scripts'
PAPERS_DIR = PROJECT_ROOT / 'papers'


def get_output_path(*subpaths: str) -> Path:
    """
    Get a path within the outputs directory.

    Args:
        *subpaths: Path components within outputs/

    Returns:
        Path object for the requested location

    Example:
        >>> get_output_path('crisis_episodes', 'summary.csv')
        PosixPath('/path/to/project/outputs/crisis_episodes/summary.csv')
    """
    return OUTPUTS_DIR.joinpath(*subpaths)


def get_data_path(*subpaths: str) -> Path:
    """
    Get a path within the data directory.

    Args:
        *subpaths: Path components within data/

    Returns:
        Path object for the requested location
    """
    return DATA_DIR.joinpath(*subpaths)


def ensure_output_dir(*subpaths: str) -> Path:
    """
    Ensure an output directory exists, creating it if necessary.

    Args:
        *subpaths: Path components within outputs/

    Returns:
        Path object for the directory (guaranteed to exist)

    Example:
        >>> output_dir = ensure_output_dir('my_analysis')
        >>> # Now safe to write files to output_dir
    """
    path = get_output_path(*subpaths)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_papers_path(paper_id: str, *subpaths: str) -> Path:
    """
    Get a path within a paper's directory.

    Args:
        paper_id: Paper identifier (e.g., 'paper1')
        *subpaths: Additional path components

    Returns:
        Path object for the requested location

    Example:
        >>> get_papers_path('paper1', 'drafts', 'v1.md')
        PosixPath('/path/to/project/papers/paper1/drafts/v1.md')
    """
    return PAPERS_DIR / paper_id / Path(*subpaths) if subpaths else PAPERS_DIR / paper_id


# For backwards compatibility with scripts that expect string paths
def get_output_path_str(*subpaths: str) -> str:
    """Get output path as string (for libraries that don't accept Path objects)."""
    return str(get_output_path(*subpaths))


def get_data_path_str(*subpaths: str) -> str:
    """Get data path as string."""
    return str(get_data_path(*subpaths))


# Environment variable support for external data (e.g., Claude session data)
def get_env_path(env_var: str, default: str = None) -> Path:
    """
    Get a path from an environment variable.

    Args:
        env_var: Environment variable name
        default: Default value if not set

    Returns:
        Path from environment variable or default

    Raises:
        ValueError if env var not set and no default provided
    """
    value = os.environ.get(env_var, default)
    if value is None:
        raise ValueError(f"Environment variable {env_var} not set and no default provided")
    return Path(value)


if __name__ == '__main__':
    # Self-test when run directly
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"OUTPUTS_DIR:  {OUTPUTS_DIR}")
    print(f"DATA_DIR:     {DATA_DIR}")
    print(f"SCRIPTS_DIR:  {SCRIPTS_DIR}")
    print(f"PAPERS_DIR:   {PAPERS_DIR}")
    print()
    print(f"Example output path: {get_output_path('crisis_episodes', 'summary.csv')}")
    print(f"Example data path:   {get_data_path('chirps', 'rasters')}")
