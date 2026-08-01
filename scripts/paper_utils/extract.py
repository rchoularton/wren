"""
Word-to-Markdown extractor.

Extracts text content from Word documents and converts to markdown format.
Used to sync Word edits back to markdown for version control.
"""

import re
from pathlib import Path
from docx import Document


def extract_text_from_word(doc_path: Path) -> str:
    """
    Extract text from a Word document and convert to markdown.

    Args:
        doc_path: Path to Word document

    Returns:
        Markdown-formatted text
    """
    doc = Document(doc_path)
    lines = []
    current_section = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            lines.append('')
            continue

        # Detect style and format accordingly
        style_name = para.style.name if para.style else 'Normal'

        if style_name == 'Title':
            lines.append(f"# {text}")
            lines.append('')
        elif style_name == 'Author':
            lines.append(text)
            lines.append('')
        elif style_name == 'Affiliation':
            lines.append(text)
            lines.append('')
        elif style_name == 'Heading1' or style_name == 'Heading 1':
            lines.append('')
            lines.append(f"## {text}")
            lines.append('')
            current_section = text.lower()
        elif style_name == 'Heading2' or style_name == 'Heading 2':
            lines.append('')
            lines.append(f"### {text}")
            lines.append('')
        elif style_name == 'Heading3' or style_name == 'Heading 3':
            lines.append('')
            lines.append(f"#### {text}")
            lines.append('')
        else:
            # Extract formatting from runs
            formatted_text = extract_formatted_text(para)
            lines.append(formatted_text)
            lines.append('')

    # Clean up multiple blank lines
    result = '\n'.join(lines)
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result.strip()


def extract_formatted_text(para) -> str:
    """Extract text from paragraph with inline formatting preserved."""
    parts = []

    for run in para.runs:
        text = run.text
        if not text:
            continue

        if run.bold and run.italic:
            parts.append(f"***{text}***")
        elif run.bold:
            parts.append(f"**{text}**")
        elif run.italic:
            parts.append(f"*{text}*")
        else:
            parts.append(text)

    return ''.join(parts)


def extract_paper(paper_id: str, output_name: str = None) -> Path:
    """
    Extract markdown from a paper's latest Word document.

    Args:
        paper_id: Paper identifier (e.g., 'paper1a')
        output_name: Optional output filename (default: extracted_v{n}.md)

    Returns:
        Path to extracted markdown file
    """
    from .paths import get_paper_config, get_drafts_dir, get_latest_word_doc

    config = get_paper_config(paper_id)
    drafts_dir = get_drafts_dir(paper_id)

    # Find Word source
    word_path = get_latest_word_doc(paper_id)
    if not word_path:
        raise FileNotFoundError(f"No Word document found in {drafts_dir}")

    # Extract content
    markdown = extract_text_from_word(word_path)

    # Determine output path
    if output_name is None:
        version = config.get('current_version', 1)
        output_name = f"extracted_v{version}.md"

    output_path = drafts_dir / output_name

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

    return output_path


def extract_to_sync(paper_id: str) -> tuple[Path, str]:
    """
    Extract markdown and return diff information.

    Returns:
        Tuple of (output_path, summary_of_changes)
    """
    from .paths import get_drafts_dir, get_latest_word_doc, get_latest_markdown

    drafts_dir = get_drafts_dir(paper_id)

    word_path = get_latest_word_doc(paper_id)
    if not word_path:
        raise FileNotFoundError(f"No Word document found in {drafts_dir}")

    # Extract current content
    new_markdown = extract_text_from_word(word_path)

    # Compare with existing markdown if present
    existing_md = get_latest_markdown(paper_id)
    if existing_md:
        with open(existing_md, 'r', encoding='utf-8') as f:
            old_markdown = f.read()

        # Simple line count comparison
        old_lines = len(old_markdown.split('\n'))
        new_lines = len(new_markdown.split('\n'))
        diff_summary = f"Lines: {old_lines} -> {new_lines} ({new_lines - old_lines:+d})"
    else:
        diff_summary = "New extraction (no previous markdown)"

    # Write to extracted file
    output_path = drafts_dir / "extracted_current.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(new_markdown)

    return output_path, diff_summary
