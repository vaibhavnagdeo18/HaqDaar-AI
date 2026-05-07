from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Numeric, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from core.database import Base

class CaseStatus(str, enum.Enum):
    onboarding = "onboarding"
    verification_pending = "verification_pending"
    audit_failed = "audit_failed"
    ready_to_submit = "ready_to_submit"
    filed = "filed"

class Case(Base):
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.id"), nullable=False)
    status = Column(Enum(CaseStatus), default=CaseStatus.onboarding)
    
    # Onboarding State
    onboarding_step = Column(Integer, default=0)
    onboarding_data = Column(JSON, default={})
    
    entitlement_total = Column(Numeric(12, 2), default=0)
    claimed_total = Column(Numeric(12, 2), default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    family = relationship("Family", back_populates="cases")
    claims = relationship("Claim", back_populates="case_info")
    disputes = relationship("Dispute", back_populates="case")
