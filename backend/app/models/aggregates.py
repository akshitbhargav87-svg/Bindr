from sqlalchemy import Column, String, ForeignKey
from backend.app.core.database import Base


class Company(Base):
    __tablename__ = "canonical_companies_v2"
    id = Column(String(80), primary_key=True)
    name = Column(String(200), nullable=False)
    registry_version = Column(String(80), nullable=False)


class CompanyAssignment(Base):
    __tablename__ = "case_company_v2"
    case_id = Column(String(36), ForeignKey("cases.id"), primary_key=True)
    company_id = Column(
        String(80), ForeignKey("canonical_companies_v2.id"), nullable=False
    )
