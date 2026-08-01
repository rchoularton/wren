#!/usr/bin/env python3
"""
Show paper sync status between project and OneDrive.

Usage:
    python status.py <paper_id>
    python status.py paper1a

Entry point for: npm run paper:status
"""

import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from paper_utils.paths import (
    get_paper_config,
    get_drafts_dir,
    resolve_onedrive_path,
    get_latest_word_doc,
    get_latest_markdown,
    list_papers
)


def format_time(timestamp: float) -> str:
    """Format timestamp as readable string."""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%b %d, %H:%M")


def get_sync_status(paper_id: str) -> dict:
    """Get detailed sync status for a paper."""
    config = get_paper_config(paper_id)
    drafts_dir = get_drafts_dir(paper_id)
    onedrive_path = config.get('onedrive_path')

    status = {
        'paper_id': paper_id,
        'title': config.get('title', 'Untitled'),
        'journal': config.get('journal', 'unknown'),
        'current_version': config.get('current_version', 1),
        'project_files': [],
        'onedrive_files': [],
        'onedrive_available': False,
        'sync_status': 'unknown',
        'suggestion': None
    }

    # List project files
    if drafts_dir.exists():
        for f in drafts_dir.iterdir():
            if f.suffix in ['.docx', '.md'] and not f.name.startswith('.'):
                status['project_files'].append({
                    'name': f.name,
                    'modified': f.stat().st_mtime,
                    'modified_str': format_time(f.stat().st_mtime),
                    'size': f.stat().st_size
                })

        # Sort by modification time
        status['project_files'].sort(key=lambda x: x['modified'], reverse=True)

    # Check OneDrive
    if onedrive_path:
        onedrive_dir = resolve_onedrive_path(onedrive_path)
        status['onedrive_path'] = str(onedrive_dir)

        if onedrive_dir.exists():
            status['onedrive_available'] = True
            for f in onedrive_dir.iterdir():
                if f.suffix in ['.docx', '.md'] and not f.name.startswith('.'):
                    status['onedrive_files'].append({
                        'name': f.name,
                        'modified': f.stat().st_mtime,
                        'modified_str': format_time(f.stat().st_mtime),
                        'size': f.stat().st_size
                    })

            status['onedrive_files'].sort(key=lambda x: x['modified'], reverse=True)
        else:
            status['sync_status'] = 'onedrive_not_found'
            status['suggestion'] = f"OneDrive path not found. Check if it exists:\n  {onedrive_dir}"
    else:
        status['sync_status'] = 'no_onedrive_config'
        status['suggestion'] = "No OneDrive path configured in config.json"

    # Determine sync status
    if status['onedrive_available'] and status['project_files'] and status['onedrive_files']:
        latest_project = status['project_files'][0]
        latest_onedrive = status['onedrive_files'][0]

        if latest_onedrive['modified'] > latest_project['modified']:
            status['sync_status'] = 'onedrive_newer'
            status['suggestion'] = f"OneDrive has newer version. Suggested:\n  cp \"{onedrive_dir / latest_onedrive['name']}\" \"{drafts_dir}/\""
        elif latest_project['modified'] > latest_onedrive['modified']:
            status['sync_status'] = 'project_newer'
            status['suggestion'] = f"Project has newer version. Suggested:\n  cp \"{drafts_dir / latest_project['name']}\" \"{onedrive_dir}/\""
        else:
            status['sync_status'] = 'synced'
            status['suggestion'] = "Files appear to be in sync."
    elif not status['project_files']:
        status['sync_status'] = 'no_project_files'
        status['suggestion'] = "No draft files in project folder."
    elif not status['onedrive_files'] and status['onedrive_available']:
        status['sync_status'] = 'no_onedrive_files'
        status['suggestion'] = "No draft files in OneDrive folder."

    return status


def print_status(status: dict):
    """Print formatted status report."""
    print(f"\n{status['title']}")
    print("=" * len(status['title']))
    print(f"Journal: {status['journal']}")
    print(f"Version: {status['current_version']}")

    print(f"\nProject folder:")
    if status['project_files']:
        for f in status['project_files'][:5]:
            print(f"  {f['name']} ({f['modified_str']}, {f['size']/1024:.1f}KB)")
    else:
        print("  (no files)")

    if status.get('onedrive_path'):
        print(f"\nOneDrive: {status['onedrive_path']}")
        if status['onedrive_available']:
            if status['onedrive_files']:
                for f in status['onedrive_files'][:5]:
                    print(f"  {f['name']} ({f['modified_str']}, {f['size']/1024:.1f}KB)")
            else:
                print("  (no files)")
        else:
            print("  (path not found)")

    print(f"\nStatus: {status['sync_status'].replace('_', ' ').title()}")
    if status['suggestion']:
        print(f"\n{status['suggestion']}")


def main():
    if len(sys.argv) < 2:
        # List all papers
        print("Paper Status Overview")
        print("=====================\n")

        papers = list_papers()
        if not papers:
            print("No papers found. Create papers/{paper_id}/config.json files.")
            sys.exit(0)

        for paper in papers:
            if 'error' in paper:
                print(f"  {paper['paper_id']}: ERROR - {paper['error']}")
            else:
                print(f"  {paper['paper_id']}: {paper.get('title', 'Untitled')} ({paper.get('journal', 'unknown')})")

        print("\nFor detailed status: python status.py <paper_id>")
        sys.exit(0)

    paper_id = sys.argv[1]

    try:
        status = get_sync_status(paper_id)
        print_status(status)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error checking status: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
