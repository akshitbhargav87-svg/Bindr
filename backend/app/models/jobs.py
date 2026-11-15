"""SQL is the durable queue. No in-process fire-and-forget tasks."""

from sqlalchemy import Column, String, Integer, BigInteger, Text
from backend.app.core.database import Base
from backend.app.models.workflow import identity
from backend.app.models.case import utc_now_iso


class Job(Base):
    __tablename__ = "platform_jobs"
    id = Column(String(36), primary_key=True, default=identity)
    owner_id = Column(String(100), nullable=False, index=True)
    case_id = Column(String(36), index=True)
    case_version = Column(Integer)
    kind = Column(String(40), nullable=False)
    state = Column(String(30), nullable=False, default="queued", index=True)
    stage = Column(String(50), nullable=False, default="queued")
    payload = Column(Text, nullable=False, default="{}")
    result = Column(Text)
    error_code = Column(String(60))
    attempts = Column(Integer, nullable=False, default=0)
    run_at = Column(BigInteger, nullable=False)
    lease_until = Column(BigInteger)
    lease_token = Column(String(36))
    created_at = Column(String(40), nullable=False, default=utc_now_iso)


class NotificationPreferences(Base):
    __tablename__ = "notification_preferences_v2"
    owner_id = Column(String(100), primary_key=True)
    version = Column(Integer, nullable=False, default=1)
    payload = Column(Text, nullable=False, default="{}")


class Export(Base):
    __tablename__ = "private_exports_v2"
    id = Column(String(36), primary_key=True, default=identity)
    owner_id = Column(String(100), nullable=False, index=True)
    case_id = Column(String(36), index=True)
    case_version = Column(Integer)
    state = Column(String(30), nullable=False, default="queued")
    storage_key = Column(String(255))
    sha256 = Column(String(64))
    media_type = Column(String(100))
    expires_at = Column(BigInteger, nullable=False)
    manifest = Column(Text)
