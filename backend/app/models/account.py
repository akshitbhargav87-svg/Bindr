"""Account identity and revocable sessions. Passwords and MFA secrets stay at Google."""
import uuid
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from backend.app.core.database import Base


class Account(Base):
    __tablename__ = "accounts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_uid = Column(String(128), nullable=False, unique=True, index=True)
    email = Column(String(320), nullable=False)
    display_name = Column(String(200), nullable=False, default="")
    created_at = Column(Integer, nullable=False)


class AccountSession(Base):
    __tablename__ = "account_sessions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    created_at = Column(Integer, nullable=False)
    expires_at = Column(Integer, nullable=False)
    auth_time = Column(Integer, nullable=False)
    factor_version = Column(String(64), nullable=False)
    user_agent = Column(String(200), nullable=False, default="")
    revoked_at = Column(Integer, nullable=True)


class WorkspaceClaim(Base):
    __tablename__ = "workspace_claims"
    # A legacy workspace may be claimed exactly once, even if its old cookie survives.
    owner_id = Column(String(100), primary_key=True)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    claimed_at = Column(Integer, nullable=False)


class AccountPreferences(Base):
    __tablename__ = "account_preferences"
    account_id = Column(String(36), ForeignKey("accounts.id"), primary_key=True)
    payload = Column(Text, nullable=False, default="{}")
    version = Column(Integer, nullable=False, default=1)


class AccountDraft(Base):
    __tablename__ = "account_drafts"
    case_id = Column(String(36), ForeignKey("cases.id"), primary_key=True)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    payload = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
