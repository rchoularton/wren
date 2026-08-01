#!/usr/bin/env python3
"""
Initialise a Tier-1 local database (SQLite or DuckDB) from data/schema.example.json.

Reads the database backend from research-config.yml. Creates tables for each
collection in the schema. Idempotent (CREATE TABLE IF NOT EXISTS).

    python3 scripts/db/init_db.py

DuckDB requires `pip install duckdb`; SQLite uses the Python standard library.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA = PROJECT_ROOT / "data" / "schema.example.json"


def backend() -> str:
    cfg = PROJECT_ROOT / "research-config.yml"
    if cfg.exists():
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(cfg.read_text()) or {}
            return (data.get("database") or {}).get("backend", "files")
        except Exception:
            pass
    return "files"


def columns_for(fields: dict) -> str:
    # Everything as TEXT for a portable starter; refine types as your schema firms up.
    cols = ", ".join(f'"{name}" TEXT' for name in fields if name != "$comment")
    return cols


def main() -> None:
    b = backend()
    if b not in ("sqlite", "duckdb"):
        print(f"database.backend is '{b}', not a Tier-1 local DB. "
              "Set it to sqlite or duckdb in research-config.yml to use this.")
        sys.exit(0)

    if not SCHEMA.exists():
        sys.exit(f"Schema not found: {SCHEMA}")
    schema = json.loads(SCHEMA.read_text())
    collections = schema.get("collections", {})

    db_path = PROJECT_ROOT / "data" / (f"research.{'duckdb' if b == 'duckdb' else 'sqlite'}")

    if b == "duckdb":
        try:
            import duckdb  # type: ignore
        except ImportError:
            sys.exit("DuckDB not installed. Run: pip install duckdb")
        con = duckdb.connect(str(db_path))
    else:
        import sqlite3
        con = sqlite3.connect(str(db_path))

    for name, spec in collections.items():
        fields = spec.get("fields", {})
        con.execute(f'CREATE TABLE IF NOT EXISTS "{name}" ({columns_for(fields)})')
        print(f"  ✓ table {name}")

    con.commit() if hasattr(con, "commit") else None
    con.close()
    print(f"\nInitialised {b} database at {db_path}")
    print("To let the assistant query it, add a SQLite/DuckDB MCP server "
          "(see docs/integrations.md).")


if __name__ == "__main__":
    main()
