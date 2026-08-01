#!/usr/bin/env bash
# setup.sh — render templates, install hooks, verify. Idempotent; re-runnable.
#
# Usage:
#   ./setup.sh                 render + install hooks + verify
#   ./setup.sh --with-schedule also install scheduled jobs (optional add-on)
#   ./setup.sh --no-verify     skip the verification step
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

WITH_SCHEDULE=0
DO_VERIFY=1
for arg in "$@"; do
  case "$arg" in
    --with-schedule) WITH_SCHEDULE=1 ;;
    --no-verify) DO_VERIFY=0 ;;
  esac
done

if [ ! -f research-config.yml ]; then
  echo "No research-config.yml found."
  echo "  cp research-config.example.yml research-config.yml   # then edit it"
  echo "  or run:  npm create research-assistant"
  exit 1
fi

# Ensure PyYAML (the only dependency the renderer needs). Best-effort across a
# few install strategies; a failed attempt must NOT abort setup (a PEP-668
# "externally-managed-environment" pip error would otherwise kill the run under
# `set -e`). If every strategy fails we stop with a clear, actionable message.
if ! python3 -c "import yaml" >/dev/null 2>&1; then
  echo "Installing PyYAML (required by the renderer)…"
  if   python3 -m pip install --quiet pyyaml >/dev/null 2>&1; then :
  elif python3 -m pip install --quiet --user pyyaml >/dev/null 2>&1; then :
  elif python3 -m pip install --quiet --break-system-packages pyyaml >/dev/null 2>&1; then :
  fi
fi
if ! python3 -c "import yaml" >/dev/null 2>&1; then
  echo "  Could not auto-install PyYAML. Install it, then re-run ./setup.sh:"
  echo "    python3 -m pip install pyyaml       (or use pipx / a virtualenv)"
  exit 1
fi

echo "→ Rendering templates…"
python3 scripts/setup/render_templates.py

echo "→ Installing hooks…"
python3 scripts/setup/install_hooks.py

if [ "$WITH_SCHEDULE" -eq 1 ]; then
  echo "→ Installing scheduled jobs…"
  if [ -f scripts/setup/install_scheduled.py ]; then
    python3 scripts/setup/install_scheduled.py
  else
    echo "  (scheduled-jobs module not installed in this build — skipping)"
  fi
fi

if [ "$DO_VERIFY" -eq 1 ]; then
  echo "→ Verifying…"
  python3 scripts/setup/verify_install.py
fi
