"""
Portable path resolution for paper management.

Uses Path(__file__).parent pattern to work from any directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """Get the project root directory."""
    # scripts/paper_utils/paths.py -> project root
    return Path(__file__).parent.parent.parent


def get_papers_dir() -> Path:
    """Get the papers directory."""
    return get_project_root() / "papers"


def get_paper_dir(paper_id: str) -> Path:
    """Get a specific paper's directory."""
    paper_dir = get_papers_dir() / paper_id
    if not paper_dir.exists():
        raise FileNotFoundError(f"Paper directory not found: {paper_dir}")
    return paper_dir


def get_paper_config(paper_id: str) -> dict:
    """Load a paper's configuration from config.json."""
    paper_dir = get_paper_dir(paper_id)
    config_path = paper_dir / "config.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Paper config not found: {config_path}")

    with open(config_path, 'r') as f:
        return json.load(f)


def resolve_onedrive_path(path_str: str) -> Path:
    """Resolve OneDrive path with ~ expansion."""
    return Path(os.path.expanduser(path_str))


def get_drafts_dir(paper_id: str) -> Path:
    """Get the drafts directory for a paper."""
    return get_paper_dir(paper_id) / "drafts"


def get_latest_word_doc(paper_id: str) -> Optional[Path]:
    """Find the latest Word document in drafts by version number."""
    drafts_dir = get_drafts_dir(paper_id)
    word_files = list(drafts_dir.glob("*.docx"))

    if not word_files:
        return None

    # Sort by modification time, newest first
    word_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return word_files[0]


def get_latest_markdown(paper_id: str) -> Optional[Path]:
    """Find the latest markdown file in drafts."""
    drafts_dir = get_drafts_dir(paper_id)
    md_files = list(drafts_dir.glob("*.md"))

    if not md_files:
        return None

    # Sort by modification time, newest first
    md_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return md_files[0]


def list_papers() -> list:
    """List all papers with their configs."""
    papers_dir = get_papers_dir()
    papers = []

    for paper_dir in papers_dir.iterdir():
        if paper_dir.is_dir() and (paper_dir / "config.json").exists():
            try:
                config = get_paper_config(paper_dir.name)
                config['paper_id'] = paper_dir.name
                papers.append(config)
            except Exception as e:
                papers.append({
                    'paper_id': paper_dir.name,
                    'error': str(e)
                })

    return papers
