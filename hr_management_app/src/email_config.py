"""
SMTP configuration.

This file reads settings from environment variables to avoid committing secrets into
source control. To run locally, set these env vars (for example in PowerShell):

# set SMTP env vars (example)
# $env:SMTP_SERVER = 'smtp.gmail.com'
# $env:SMTP_PORT = '465'
# $env:SMTP_USE_SSL = 'True'
# $env:SMTP_USER = 'you@example.com'
# $env:SMTP_PASSWORD = 'your-app-password'
# $env:FROM_EMAIL = 'you@example.com'

If you prefer a local file, create `email_config_local.py` (gitignored) with the same
names and values and import it from here instead. By default values are read from the
environment and fall back to safe defaults.
"""

import os

# Read SMTP config from environment. Defaults are conservative so the app
# will not attempt to send emails unless credentials are explicitly provided.
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "False").lower() in ("1", "true", "yes")
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", SMTP_USER or "no-reply@example.com")

# Consider SMTP configured only when server and credentials are provided.
SMTP_CONFIGURED = bool(SMTP_SERVER and SMTP_USER and SMTP_PASSWORD)