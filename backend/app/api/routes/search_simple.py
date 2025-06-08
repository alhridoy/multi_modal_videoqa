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
    """Generate simple, effective search suggestions based on video content"""
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # Simple suggestion logic based on video type and title
        suggestions = []
        
        if video.video_type == "youtube":
            title_lower = video.title.lower()
            
            # Context-aware suggestions based on video title
            if any(word in title_lower for word in ['interview', 'talk', 'discussion']):
                suggestions = ["person speaking", "microphone", "interviewer", "guest", "office background"]
            elif any(word in title_lower for word in ['demo', 'tutorial', 'how to']):
                suggestions = ["screen", "computer", "demonstration", "presenter", "tutorial"]
            elif any(word in title_lower for word in ['review', 'unbox']):
                suggestions = ["product", "hands", "table", "packaging", "close-up"]
            elif any(word in title_lower for word in ['car', 'drive', 'vehicle']):
                suggestions = ["red car", "vehicle", "driving", "road", "dashboard"]
            elif any(word in title_lower for word in ['music', 'song', 'performance']):
                suggestions = ["performer", "stage", "microphone", "audience", "instrument"]
            else:
                # General video suggestions
                suggestions = ["person", "speaker", "background", "text on screen", "object"]
        else:
            # Default suggestions for uploaded videos
            suggestions = ["person", "object", "text on screen", "background", "vehicle"]
        
        return {
            "video_id": video_id,
            "suggestions": suggestions[:8],  # Limit to 8 suggestions
            "total_suggestions": len(suggestions),
            "generation_method": "simple_title_based"
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