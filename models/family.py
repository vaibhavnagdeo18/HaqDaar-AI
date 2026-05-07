from sqlalchemy import Column, String, Date, DateTime, JSON, Enum, Float, Boolean, ForeignKey, Numeric, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from core.database import Base

class Family(Base):
    __tablename__ = "families"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    whatsapp_number = Column(String, unique=True, index=True, nullable=False)
    preferred_language = Column(String)  # 'Telugu', 'Hindi', 'Tamil', etc.
    state = Column(String)
    district = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), onupdate=func.now())

    # Breadwinner details
    breadwinner_name = Column(String)
    breadwinner_dob = Column(Date)
    date_of_death = Column(Date)
    cause_of_death = Column(String)  # 'natural', 'accident', 'occupational'
    employment_type = Column(String)  # 'organized', 'unorganized', 'government', 'self_employed'
    employer_name = Column(String)
    epf_account_number = Column(String)
    uan_number = Column(String)

    # Claimant details
    claimant_name = Column(String)
    claimant_relationship = Column(String)  # 'spouse', 'child', 'parent'
    claimant_aadhaar = Column(String)  # Encrypted in real life
    claimant_bank_account = Column(String)  # Encrypted in real life
    claimant_bank_ifsc = Column(String)
    
    # Relationships
    cases = relationship("Case", back_populates="family")
    documents = relationship("Document", back_populates="family")
    conversations = relationship("Conversation", back_populates="family")
