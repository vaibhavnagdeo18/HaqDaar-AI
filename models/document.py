from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON, Float, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from core.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.id"), nullable=False)
    
    document_type = Column(String, nullable=False)  # 'death_certificate', 'aadhaar', 'passbook'
    file_path = Column(String, nullable=False)
    
    quality_score = Column(Float)  # 0-1
    issues = Column(JSON)  # ['missing_seal', 'blurry', 'incomplete']
    is_valid = Column(Boolean, default=False)
    
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    extracted_data = Column(JSON)  # OCR-extracted fields

    # Relationships
    family = relationship("Family", back_populates="documents")
