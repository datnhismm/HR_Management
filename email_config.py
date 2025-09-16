# Top-level shim to import project email config from package
try:
    # prefer package-local config when running from package
    from hr_management_app.src.email_config import *  # type: ignore
except Exception:
    # fallback minimal defaults
    FROM_EMAIL = "noreply@example.local"
    SMTP_CONFIGURED = False
    SMTP_SERVER = ""
    SMTP_PORT = 587
    SMTP_USE_SSL = False
    SMTP_USER = ""
    SMTP_PASSWORD = ""
