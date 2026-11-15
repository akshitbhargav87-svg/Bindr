from sqlalchemy import Column, String, Integer
from backend.app.core.database import Base
from backend.app.models.workflow import identity


class PushDevice(Base):
    __tablename__ = "private_push_devices_v2"
    id = Column(String(36), primary_key=True, default=identity)
    owner_id = Column(String(100), nullable=False, index=True)
    token_digest = Column(String(64), nullable=False, unique=True)
    credential = Column(String(12000), nullable=False)
    active = Column(Integer, nullable=False, default=1)
