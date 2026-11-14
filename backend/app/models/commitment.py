import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Commitment(Base):
    __tablename__ = "commitments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    extraction_id = Column(String(36), nullable=True)
    candidate_id = Column(String(50), nullable=True)
    kind = Column(String(50), nullable=False, default="refund")  # refund, replacement, service, other
    description = Column(Text, nullable=False)
    amount_minor = Column(Integer, nullable=True)
    currency = Column(String(3), nullable=True)
    due_at = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="active")  # active, superseded, fulfilled
    supersedes_id = Column(String(36), ForeignKey("commitments.id", ondelete="SET NULL"), nullable=True, index=True)
    _evidence_ids = Column("evidence_ids", Text, nullable=False, default="[]")
    reviewed_at = Column(String(50), nullable=True)
    created_at = Column(String(50), nullable=False, default=utc_now_iso)

    # Property for evidence_ids list
    @property
    def evidence_ids(self) -> List[str]:
        if not self._evidence_ids:
            return []
        try:
            return json.loads(self._evidence_ids)
        except Exception:
            return []

    @evidence_ids.setter
    def evidence_ids(self, val: List[str]):
        self._evidence_ids = json.dumps(val or [])

    # Relationships
    case = relationship("Case", back_populates="commitments")
    superseded_by = relationship(
        "Commitment",
        backref="supersedes",
        remote_side=[id],
        foreign_keys=[supersedes_id]
    )
