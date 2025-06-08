from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import logging

from app.core.database import get_db
from app.models.video import Video, ChatMessage
from app.services.gemini_service import GeminiService
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)
router = APIRouter()

class ChatRequest(BaseModel):
    video_id: int
    message: str

class ChatResponse(BaseModel):
    response: str
    citations: List[dict]
    message_id: int

@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    request: Request,
    chat_request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Send a chat message about a video"""
    try:
        # Get video
        video = db.query(Video).filter(Video.id == chat_request.video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Initialize services
        gemini_service = request.app.state.gemini_service
        vector_service = VectorService()
        
        # Get relevant context using vector search
        relevant_context = ""
        if vector_service.available and video.transcript:
            # Search for relevant transcript segments
            search_results = await vector_service.search_transcript(
                query=chat_request.message,
                video_id=chat_request.video_id,
                limit=3
            )
            
            if search_results:
                relevant_context = "\n\nRelevant video segments:\n"
                for result in search_results:
                    relevant_context += f"- {result['text']}\n"
        
        # Use full transcript or relevant context
        transcript_text = relevant_context if relevant_context else (video.transcript or "No transcript available for this video.")
        
        # Get chat history
        chat_history = db.query(ChatMessage)\
            .filter(ChatMessage.video_id == chat_request.video_id)\
            .order_by(ChatMessage.created_at.desc())\
            .limit(10)\
            .all()
        
        # Prepare chat history for AI
        history_data = [
            {
                "message": msg.message,
                "response": msg.response
            }
            for msg in reversed(chat_history)
        ]
        
        # Generate AI response
        ai_response = await gemini_service.generate_chat_response(
            question=chat_request.message,
            transcript=transcript_text,
            video_info={
                "title": video.title,
                "duration": video.duration
            },
            chat_history=history_data
        )
        
        if ai_response["status"] != "success":
            raise HTTPException(
                status_code=500,
                detail="Failed to generate AI response"
            )
        
        # Save chat message
        chat_message = ChatMessage(
            video_id=chat_request.video_id,
            message=chat_request.message,
            response=ai_response["response"],
            citations=ai_response["citations"]
        )
        db.add(chat_message)
        db.commit()
        db.refresh(chat_message)
        
        return ChatResponse(
            response=ai_response["response"],
            citations=ai_response["citations"],
            message_id=chat_message.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{video_id}/history")
async def get_chat_history(
    video_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get chat history for a video"""
    # Verify video exists
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Get chat messages
    messages = db.query(ChatMessage)\
        .filter(ChatMessage.video_id == video_id)\
        .order_by(ChatMessage.created_at.asc())\
        .limit(limit)\
        .all()
    
    return {
        "video_id": video_id,
        "messages": [
            {
                "id": msg.id,
                "message": msg.message,
                "response": msg.response,
                "citations": msg.citations,
                "created_at": msg.created_at
            }
            for msg in messages
        ]
    }

@router.delete("/{video_id}/history")
async def clear_chat_history(
    video_id: int,
    db: Session = Depends(get_db)
):
    """Clear chat history for a video"""
    # Verify video exists
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Delete chat messages
    deleted_count = db.query(ChatMessage)\
        .filter(ChatMessage.video_id == video_id)\
        .delete()
    
    db.commit()
    
    return {
        "message": f"Cleared {deleted_count} chat messages",
        "video_id": video_id
    }
