#!/usr/bin/env python3
"""Create admin (moved)."""
from pathlib import Path
import secrets
try:
    from database import database as db
except Exception:
    from hr_management_app.src.database import database as db

DEFAULT_EMAIL = 'admin@example.com'

def gen_password(length=16):
    return secrets.token_urlsafe(length)[:length]

def main():
    email = input(f'Email [{DEFAULT_EMAIL}]: ').strip() or DEFAULT_EMAIL
    pwd = gen_password(20)
    user_id = db.create_user(email=email, password=pwd, role='admin')
    print('Admin created: id=', user_id)
    print('Email:', email)
    print('Password:', pwd)

if __name__ == '__main__':
    main()
