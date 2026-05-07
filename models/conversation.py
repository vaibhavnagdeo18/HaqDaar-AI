from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from core.database import Base

class MessageDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"

class MessageType(str, enum.Enum):
    text = "text"
    voice = "voice"
    document = "document"
    image = "image"
    interactive = "interactive"

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.id"), nullable=False)
    
    whatsapp_message_id = Column(String, unique=True)
    direction = Column(Enum(MessageDirection))
    message_type = Column(Enum(MessageType))
    
    content = Column(Text)  # transcribed if voice
    original_language = Column(String)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    agent_handled_by = Column(String)  # which agent processed this

    # Relationships
    family = relationship("Family", back_populates="conversations")
