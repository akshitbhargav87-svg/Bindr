import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    media_type = Column(String(100), nullable=False, default="text/plain")
    size_bytes = Column(Integer, nullable=False, default=0)
    sha256 = Column(String(64), nullable=False, default="")
    download_path = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False, default=utc_now_iso)

    # Relationships
    case = relationship("Case", back_populates="evidence")
