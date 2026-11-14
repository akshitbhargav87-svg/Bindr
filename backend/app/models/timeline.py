import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    event_date = Column(String(50), nullable=False, default=utc_now_iso)
    created_at = Column(String(50), nullable=False, default=utc_now_iso)

    # Relationships
    case = relationship("Case", back_populates="timeline_events")
