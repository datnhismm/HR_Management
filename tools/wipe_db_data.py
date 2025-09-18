#!/usr/bin/env python3
"""Launcher for db/wipe_db_data (moved to tools/db)."""
import runpy

runpy.run_path("tools/db/wipe_db_data.py", run_name="__main__")
