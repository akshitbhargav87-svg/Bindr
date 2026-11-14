"""Vulnerability diagnostic only: no registered session, real identity, or auth override."""
import secrets

def authenticate(client, session):
    # Never print the value. Its acceptance demonstrates weak auth, not successful login.
    client.cookies.set('pk_session', secrets.token_urlsafe(32))
