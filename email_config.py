# Top-level shim to import project email config from package
try:
    # prefer package-local config when running from package
    from hr_management_app.src import email_config as _pkg_email_config  # type: ignore

    FROM_EMAIL = getattr(_pkg_email_config, "FROM_EMAIL", "noreply@example.local")
    SMTP_CONFIGURED = getattr(_pkg_email_config, "SMTP_CONFIGURED", False)
    SMTP_SERVER = getattr(_pkg_email_config, "SMTP_SERVER", "")
    SMTP_PORT = getattr(_pkg_email_config, "SMTP_PORT", 587)
    SMTP_USE_SSL = getattr(_pkg_email_config, "SMTP_USE_SSL", False)
    SMTP_USER = getattr(_pkg_email_config, "SMTP_USER", "")
    SMTP_PASSWORD = getattr(_pkg_email_config, "SMTP_PASSWORD", "")
except Exception:
    # fallback minimal defaults
    FROM_EMAIL = "noreply@example.local"
    SMTP_CONFIGURED = False
    SMTP_SERVER = ""
    SMTP_PORT = 587
    SMTP_USE_SSL = False
    SMTP_USER = ""
    SMTP_PASSWORD = ""
