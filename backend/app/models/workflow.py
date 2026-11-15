"""Versioned platform records. V1 commitments remain unchanged during v2 rollout."""

import uuid
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from backend.app.core.database import Base
from backend.app.models.case import utc_now_iso


def identity():
    return str(uuid.uuid4())


class Obligation(Base):
    __tablename__ = "obligations_v2"
    id = Column(String(36), primary_key=True, default=identity)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    root_id = Column(String(36), nullable=False, index=True)
    predecessor_id = Column(String(36), ForeignKey("obligations_v2.id"))
    state = Column(String(30), nullable=False, default="active")
    origin = Column(String(30), nullable=False)
    terms = Column(Text, nullable=False)
    sources = Column(Text, nullable=False)
    deadline = Column(Text, nullable=False, default="{}")
    created_at = Column(String(40), nullable=False, default=utc_now_iso)


class CaseEvent(Base):
    __tablename__ = "case_events_v2"
    id = Column(String(36), primary_key=True, default=identity)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    kind = Column(String(40), nullable=False)
    payload = Column(Text, nullable=False)
    case_version = Column(Integer)
    sequence = Column(Integer)
    created_at = Column(String(40), nullable=False, default=utc_now_iso)


class Proposal(Base):
    __tablename__ = "proposals_v2"
    id = Column(String(80), primary_key=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    case_version = Column(Integer, nullable=False)
    payload = Column(Text, nullable=False)
    state = Column(String(30), nullable=False, default="review_required")
    created_at = Column(String(40), nullable=False, default=utc_now_iso)


class CaseControl(Base):
    __tablename__ = "case_control_v2"
    case_id = Column(String(36), ForeignKey("cases.id"), primary_key=True)
    owner_id = Column(String(100), nullable=False, index=True)
    state = Column(String(30), nullable=False, default="open")
    deleted_at = Column(String(40))
