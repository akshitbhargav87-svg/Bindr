from sqlalchemy import Column, String, Integer, Text, UniqueConstraint
from backend.app.core.database import Base
from backend.app.models.workflow import identity
from backend.app.models.case import utc_now_iso


class Connection(Base):
    __tablename__ = "provider_connections_v2"
    id = Column(String(36), primary_key=True, default=identity)
    owner_id = Column(String(100), nullable=False, index=True)
    provider = Column(String(30), nullable=False)
    state = Column(String(30), nullable=False, default="connected")
    credential = Column(
        Text
    )  # AES-GCM ciphertext; no access/refresh token in API responses
    scopes = Column(Text, nullable=False, default="[]")
    generation = Column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("owner_id", "provider"),)


class OAuthState(Base):
    __tablename__ = "oauth_states_v2"
    digest = Column(String(64), primary_key=True)
    owner_id = Column(String(100), nullable=False)
    session_id = Column(String(100), nullable=False)
    verifier = Column(Text, nullable=False)
    scopes = Column(Text, nullable=False)
    expires_at = Column(Integer, nullable=False)
    used_at = Column(Integer)


class IntakeAlias(Base):
    __tablename__ = "intake_aliases_v2"
    digest = Column(String(64), primary_key=True)
    owner_id = Column(String(100), nullable=False, index=True)
    case_id = Column(String(36))
    revoked_at = Column(Integer)


class Intake(Base):
    __tablename__ = "private_intake_v2"
    id = Column(String(36), primary_key=True, default=identity)
    owner_id = Column(String(100), nullable=False, index=True)
    case_id = Column(String(36))
    provider = Column(String(30), nullable=False)
    event_id = Column(String(200), nullable=False)
    message_hash = Column(String(64), nullable=False)
    storage_key = Column(String(255), nullable=False)
    state = Column(String(30), nullable=False, default="review_required")
    created_at = Column(String(40), nullable=False, default=utc_now_iso)
    __table_args__ = (
        UniqueConstraint("provider", "event_id"),
        UniqueConstraint("owner_id", "case_id", "message_hash"),
    )


class AccountControl(Base):
    __tablename__ = "account_control_v2"
    owner_id = Column(String(100), primary_key=True)
    state = Column(String(30), nullable=False, default="active")
    deleted_at = Column(Integer)


class AggregateConsent(Base):
    __tablename__ = "aggregate_consent_v2"
    owner_id = Column(String(100), primary_key=True)
    enabled = Column(Integer, nullable=False, default=0)
    version = Column(Integer, nullable=False, default=1)


class ProviderLink(Base):
    __tablename__ = "provider_links_v2"
    provider = Column(String(30), primary_key=True)
    remote_digest = Column(String(64), primary_key=True)
    owner_id = Column(String(100), nullable=False, index=True)
    alias_digest = Column(String(64), nullable=False)


class MessageIdentity(Base):
    __tablename__ = "intake_message_identity_v2"
    owner_id = Column(String(100), primary_key=True)
    case_scope = Column(String(40), primary_key=True)
    message_digest = Column(String(64), primary_key=True)
    body_hash = Column(String(64), nullable=False)
    intake_id = Column(String(36), nullable=False)
