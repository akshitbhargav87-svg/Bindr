import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(100), nullable=False, default="demo-user")
    title = Column(String(200), nullable=False)
    merchant_name = Column(String(200), nullable=False)
    status = Column(String(50), nullable=False, default="open")  # open, overdue, resolved
    version = Column(Integer, nullable=False, default=1)
    resolution_note = Column(Text, nullable=True)
    resolved_at = Column(String(50), nullable=True)
    created_at = Column(String(50), nullable=False, default=utc_now_iso)

    # Relationships
    commitments = relationship("Commitment", back_populates="case", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="case", cascade="all, delete-orphan")
    extractions = relationship("Extraction", back_populates="case", cascade="all, delete-orphan")
