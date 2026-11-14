import json
import uuid
from typing import List, Dict, Any
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.case import utc_now_iso


class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    _evidence_ids = Column("evidence_ids", Text, nullable=False, default="[]")
    _candidates = Column("candidates", Text, nullable=False, default="[]")
    status = Column(String(50), nullable=False, default="pending_review")  # pending_review, reviewed, rejected
    _reviewed_commitment_ids = Column("reviewed_commitment_ids", Text, nullable=False, default="[]")
    created_at = Column(String(50), nullable=False, default=utc_now_iso)

    # Relationship
    case = relationship("Case", back_populates="extractions")

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

    @property
    def candidates(self) -> List[Dict[str, Any]]:
        if not self._candidates:
            return []
        try:
            return json.loads(self._candidates)
        except Exception:
            return []

    @candidates.setter
    def candidates(self, val: List[Dict[str, Any]]):
        self._candidates = json.dumps(val or [])

    @property
    def reviewed_commitment_ids(self) -> List[str]:
        if not self._reviewed_commitment_ids:
            return []
        try:
            return json.loads(self._reviewed_commitment_ids)
        except Exception:
            return []

    @reviewed_commitment_ids.setter
    def reviewed_commitment_ids(self, val: List[str]):
        self._reviewed_commitment_ids = json.dumps(val or [])
