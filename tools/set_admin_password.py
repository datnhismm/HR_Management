#!/usr/bin/env python3
"""Launcher for admin/set_admin_password (moved to tools/admin)."""
import runpy

runpy.run_path("tools/admin/set_admin_password.py", run_name="__main__")
