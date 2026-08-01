#!/usr/bin/env python3
"""
Extract markdown from Word document.

Usage:
    python extract_cli.py <paper_id> [output_name]
    python extract_cli.py paper1a
    python extract_cli.py paper1a draft_v8.md

Entry point for: npm run paper:extract
"""

import sys
from pathlib import Path

# Add parent to path for imports when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from paper_utils.extract import extract_paper, extract_to_sync
from paper_utils.paths import get_latest_word_doc


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_cli.py <paper_id> [output_name]")
        print("\nExamples:")
        print("  python extract_cli.py paper1a                # Extract to extracted_v{n}.md")
        print("  python extract_cli.py paper1a draft_v8.md    # Extract to specific file")
        print("  python extract_cli.py paper1a --sync         # Extract and show diff summary")
        sys.exit(1)

    paper_id = sys.argv[1]

    try:
        # Check for Word source
        word_path = get_latest_word_doc(paper_id)
        if not word_path:
            print(f"Error: No Word document found for {paper_id}")
            print("Add a Word document to papers/{paper_id}/drafts/")
            sys.exit(1)

        print(f"Extracting markdown from {paper_id}")
        print(f"  Source: {word_path.name}")

        # Handle --sync option
        if len(sys.argv) > 2 and sys.argv[2] == '--sync':
            output_path, diff_summary = extract_to_sync(paper_id)
            print(f"\nExtracted: {output_path}")
            print(f"Changes: {diff_summary}")
        else:
            output_name = sys.argv[2] if len(sys.argv) > 2 else None
            output_path = extract_paper(paper_id, output_name)
            print(f"\nSuccess! Created: {output_path}")
            print(f"  Size: {output_path.stat().st_size / 1024:.1f} KB")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error extracting document: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
