"""
Paper utilities for managing research paper drafts.

This module provides tools for:
- Converting markdown to formatted Word documents
- Extracting Word content back to markdown
- Managing OneDrive sync status
- Journal-specific formatting styles
"""

from .paths import get_paper_config, get_paper_dir, resolve_onedrive_path
from .styles import JOURNAL_STYLES, apply_journal_styles

__all__ = [
    'get_paper_config',
    'get_paper_dir',
    'resolve_onedrive_path',
    'JOURNAL_STYLES',
    'apply_journal_styles',
]
