"""
Simple Search Routes

This replaces the overengineered search.py with a clean, effective implementation
that focuses on delivering results, not complex architectures.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import logging
import os

from app.core.database import get_db
from app.models.video import Video
from app.services.simple_video_search import simple_search, VideoSearchResponse

logger = logging.getLogger(__name__)
router = APIRouter()

class VisualSearchRequest(BaseModel):
    video_id: int
    query: str
    max_results: int = 10

@router.post("/visual", response_model=VideoSearchResponse)
async def visual_search(
    request: Request,
    search_request: VisualSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Simple visual search that actually works.
    
    Uses the best available method:
    1. Native Gemini 2.5 video analysis (if available)
    2. Direct frame analysis (fallback)
    
    No complex fallback chains, no redundant systems.
    """
    try:
        # Get video
        video = db.query(Video).filter(Video.id == search_request.video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        if not video.file_path or not os.path.exists(video.file_path):
            raise HTTPException(status_code=400, detail="Video file not found")
        
        # Initialize simple search with Gemini service
        simple_search.initialize_gemini(request.app.state.gemini_service)
        
        # Perform search
        response = await simple_search.search(
            video_path=video.file_path,
            query=search_request.query,
            video_id=search_request.video_id
        )
        
        logger.info(f"Search '{search_request.query}' completed using {response.processing_method}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{video_id}/suggestions")
async def get_search_suggestions(
    request: Request,
    video_id: int,
    db: Session = Depends(get_db)
):
    """Generate smart search suggestions from video content and transcript"""
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        suggestions = []
        generation_method = "content_based"

        # METHOD 1: Extract from transcript if available
        if video.transcript:
            try:
                gemini_service = request.app.state.gemini_service
                prompt = f"""
                Analyze this video transcript and generate 8 specific visual search terms that would help someone find interesting moments in the video.

                Focus on:
                - Objects, people, and visual elements mentioned
                - Actions and activities described
                - Settings and environments
                - Specific items that would be visually identifiable

                Transcript: {video.transcript[:2000]}...

                Return only a comma-separated list of 8 search terms, no explanations.
                Example: person speaking, microphone, computer screen, whiteboard, coffee cup, office chair, presentation slide, hand gesture
                """

                response = gemini_service.model.generate_content(prompt)
                response = response.text if response else ""
                if response and response.strip():
                    # Parse the response
                    suggested_terms = [term.strip() for term in response.split(',')]
                    suggestions = [term for term in suggested_terms if term and len(term) > 2][:8]
                    generation_method = "ai_transcript_analysis"

            except Exception as e:
                logger.warning(f"AI suggestion generation failed: {e}")

        # METHOD 2: Fallback to title-based suggestions
        if not suggestions:
            title_lower = video.title.lower()

            # Context-aware suggestions based on video title
            if any(word in title_lower for word in ['interview', 'talk', 'discussion', 'conversation']):
                suggestions = ["person speaking", "microphone", "interviewer", "guest", "office background", "desk", "chair", "gestures"]
            elif any(word in title_lower for word in ['demo', 'tutorial', 'how to', 'guide']):
                suggestions = ["screen", "computer", "demonstration", "presenter", "keyboard", "mouse", "software", "interface"]
            elif any(word in title_lower for word in ['review', 'unbox', 'product']):
                suggestions = ["product", "hands", "table", "packaging", "close-up", "box", "item", "comparison"]
            elif any(word in title_lower for word in ['ai', 'technology', 'software', 'coding']):
                suggestions = ["computer", "screen", "code", "interface", "person", "presentation", "diagram", "text"]
            elif any(word in title_lower for word in ['business', 'keynote', 'conference']):
                suggestions = ["presenter", "stage", "audience", "screen", "microphone", "podium", "slides", "logo"]
            else:
                # Smart general suggestions
                suggestions = ["person", "speaker", "screen", "text", "background", "object", "hands", "face"]

            generation_method = "enhanced_title_based"

        return {
            "video_id": video_id,
            "suggestions": suggestions[:8],  # Limit to 8 suggestions
            "total_suggestions": len(suggestions),
            "generation_method": generation_method
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Essential endpoints that other functionality depends on
@router.get("/{video_id}/frames")
async def get_video_frames(
    video_id: int,
    limit: int = 100,  # Reduced from 500 
    db: Session = Depends(get_db)
):
    """Get video frames (simplified)"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    from app.models.video import VideoFrame
    frames = db.query(VideoFrame)\
        .filter(VideoFrame.video_id == video_id)\
        .order_by(VideoFrame.timestamp.asc())\
        .limit(limit)\
        .all()
    
    return {
        "video_id": video_id,
        "frames": [
            {
                "id": frame.id,
                "timestamp": frame.timestamp,
                "frame_path": frame.frame_path,
                "description": frame.description
            }
            for frame in frames
        ]
    }

@router.get("/{video_id}/frame")
async def get_video_frame_at_timestamp(
    video_id: int,
    timestamp: float,
    size: str = "medium",
    db: Session = Depends(get_db)
):
    """Extract frame at specific timestamp (simplified)"""
    try:
        from fastapi.responses import FileResponse
        import cv2
        import tempfile
        
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        if not video.file_path:
            raise HTTPException(status_code=404, detail="Video file not found")
        
        # Direct frame extraction
        cap = cv2.VideoCapture(video.file_path)
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_number = int(timestamp * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            ret, frame = cap.read()
            if not ret:
                raise HTTPException(status_code=404, detail="Could not extract frame")
            
            # Simple size mapping
            sizes = {"small": (160, 90), "medium": (320, 180), "large": (640, 360)}
            target_size = sizes.get(size, sizes["medium"])
            frame = cv2.resize(frame, target_size)
            
            # Save and return
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                cv2.imwrite(tmp.name, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                return FileResponse(
                    tmp.name,
                    media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=3600"}
                )
                
        finally:
            cap.release()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting frame: {e}")
        raise HTTPException(status_code=500, detail=str(e))