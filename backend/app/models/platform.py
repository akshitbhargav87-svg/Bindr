"""Account-scoped v2 primitives. Immutable originals and existing account tables are retained."""

import uuid
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from backend.app.core.database import Base
from backend.app.models.case import utc_now_iso


class Operation(Base):
    __tablename__ = "platform_operations"
    owner_id = Column(String(100), primary_key=True)
    scope = Column(String(180), primary_key=True)
    key = Column(String(200), primary_key=True)
    payload_hash = Column(String(64), nullable=False)
    result = Column(Text, nullable=True)
    created_at = Column(String(40), nullable=False, default=utc_now_iso)


class CaptureDraft(Base):
    __tablename__ = "capture_drafts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(100), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    payload = Column(Text, nullable=False)
    updated_at = Column(String(40), nullable=False, default=utc_now_iso)


class EvidenceCommunication(Base):
    __tablename__ = "evidence_communication"
    evidence_id = Column(String(36), ForeignKey("evidence.id"), primary_key=True)
    payload = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
