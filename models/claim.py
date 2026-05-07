from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from core.database import Base

class ClaimStatus(str, enum.Enum):
    eligible = "eligible"
    ready = "ready"
    filed = "filed"
    approved = "approved"
    rejected = "rejected"

class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    
    scheme_id = Column(String, nullable=False)
    scheme_name = Column(String, nullable=False)
    estimated_benefit = Column(Numeric(12, 2), default=0)
    
    status = Column(Enum(ClaimStatus), default=ClaimStatus.eligible)
    form_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    case_info = relationship("Case", back_populates="claims")
