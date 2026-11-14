"""Test-only trusted session issuance; no login endpoint or auth dependency override."""
from backend.app.core.auth import create_authenticated_session


def authenticate(client, session):
    # Runner provisions a fresh private test signing secret before production import.
    # Issuance is trusted fixture setup, not proof that a browser can log in.
    token, csrf = create_authenticated_session(user_id='synthetic-regression-user')
    client.cookies.set('pk_session', token)
    client.cookies.set('pk_csrf', csrf)
    client.headers['X-CSRF-Token'] = csrf
    client.headers['Origin'] = 'http://localhost:5173'
