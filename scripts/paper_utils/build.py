#!/usr/bin/env python3
"""
Build Word document from markdown source.

Usage:
    python build.py <paper_id> [version]
    python build.py paper1a
    python build.py paper1a 8

Entry point for: npm run paper:build
"""

import sys
from pathlib import Path

# Add parent to path for imports when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from paper_utils.word_builder import build_paper
from paper_utils.paths import get_paper_config, get_latest_markdown


def main():
    if len(sys.argv) < 2:
        print("Usage: python build.py <paper_id> [version]")
        print("\nExamples:")
        print("  python build.py paper1a      # Build with default version")
        print("  python build.py paper1a 8    # Build as version 8")
        sys.exit(1)

    paper_id = sys.argv[1]
    version = int(sys.argv[2]) if len(sys.argv) > 2 else None

    try:
        # Check for markdown source
        md_path = get_latest_markdown(paper_id)
        if not md_path:
            print(f"Error: No markdown file found for {paper_id}")
            print("Create a markdown source file in papers/{paper_id}/drafts/")
            sys.exit(1)

        # Get config for journal info
        config = get_paper_config(paper_id)
        journal = config.get('journal', 'default')

        print(f"Building Word document for {paper_id}")
        print(f"  Source: {md_path.name}")
        print(f"  Journal: {journal}")

        output_path = build_paper(paper_id, version)

        print(f"\nSuccess! Created: {output_path}")
        print(f"  Size: {output_path.stat().st_size / 1024:.1f} KB")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error building document: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
