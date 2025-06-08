from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class Video(Base):
    """Video model for storing video metadata and analysis results"""
    
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    video_type = Column(String(50), nullable=False)  # 'youtube', 'upload'
    youtube_id = Column(String(20), nullable=True)
    file_path = Column(String(500), nullable=True)
    duration = Column(Float, nullable=True)
    
    # Processing status
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    transcript = Column(Text, nullable=True)
    sections = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Analysis results
    frame_count = Column(Integer, default=0)
    embedding_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    analysis_metadata = Column(JSON, nullable=True)  # Additional metadata for storing analysis results

class VideoFrame(Base):
    """Video frame model for storing extracted frames and embeddings"""
    
    __tablename__ = "video_frames"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(Float, nullable=False)
    frame_path = Column(String(500), nullable=False)
    
    # Embeddings and analysis
    embedding_id = Column(String(100), nullable=True)  # ChromaDB ID
    description = Column(Text, nullable=True)
    objects_detected = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChatMessage(Base):
    """Chat message model for storing conversation history"""
    
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, nullable=False, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True)  # List of timestamp citations
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
