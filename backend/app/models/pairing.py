from sqlalchemy import Column, String, Integer
from backend.app.core.database import Base


class CaptureCapability(Base):
    __tablename__ = "capture_capabilities_v2"
    digest = Column(String(64), primary_key=True)
    owner_id = Column(String(100), nullable=False, index=True)
    session_id = Column(String(100))
    case_id = Column(String(36), nullable=False)
    expires_at = Column(Integer, nullable=False)
    used_at = Column(Integer)
    result = Column(String(36))
    payload_hash = Column(String(64))
