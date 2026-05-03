from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from .database import Base


class MemeRequest(Base):
    __tablename__ = "meme_requests"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)

    deleted      = Column(Boolean, nullable=False, default=False)
    current_step = Column(String(30), nullable=True)

    started_at          = Column(DateTime(timezone=True), nullable=False)
    ocr_done_at         = Column(DateTime(timezone=True), nullable=True)
    remove_text_done_at = Column(DateTime(timezone=True), nullable=True)
    caption_done_at     = Column(DateTime(timezone=True), nullable=True)
    translate_done_at   = Column(DateTime(timezone=True), nullable=True)
    completed_at        = Column(DateTime(timezone=True), nullable=True)

    ocr_retries              = Column(Integer, default=0)
    caption_retries          = Column(Integer, default=0)
    humor_analysis_retries   = Column(Integer, default=0)
    translation_retries      = Column(Integer, default=0)

    ocr_blocks     = Column(JSONB, nullable=True)
    ocr_full_text  = Column(Text,  nullable=True)
    visual_context = Column(Text,  nullable=True)
    humor_analysis = Column(Text,  nullable=True)
    explanation_ru = Column(Text,  nullable=True)
    explanation_en = Column(Text,  nullable=True)
    full_text_en   = Column(Text,  nullable=True)
    blocks_en      = Column(JSONB, nullable=True)

    original_image_url = Column(Text, nullable=True)
    clean_image_url    = Column(Text, nullable=True)
    result_image_url   = Column(Text, nullable=True)

    status = Column(String(20), nullable=False, default="processing")
    error  = Column(Text, nullable=True)
