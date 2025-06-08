from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging
import asyncio
from typing import Dict

from app.core.database import get_db
from app.models.video import Video, VideoFrame
from app.services.youtube_service import YouTubeService
# Enhanced services (require additional dependencies)
try:
    from app.services.youtube_optimizer import YouTubeOptimizer
    ENHANCED_PROCESSING_AVAILABLE = True
except ImportError:
    ENHANCED_PROCESSING_AVAILABLE = False
# Frame analysis functionality removed for stability

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage for processing status (in production, use Redis or similar)
processing_status: Dict[int, Dict] = {}

async def process_youtube_video_background(
    request: Request,
    video_id: int,
    youtube_id: str,
    youtube_url: str,
    use_optimizer: bool = True,
    enable_visual_search: bool = True
):
    """Background task to process YouTube video"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Get video record
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found in database")
            return
        
        # Update status
        processing_status[video_id] = {
            "status": "processing",
            "progress": 10,
            "message": "Initializing video processing...",
            "stage": "initialization"
        }
        
        # Use optimizer if available and requested
        if use_optimizer and ENHANCED_PROCESSING_AVAILABLE:
            try:
                youtube_optimizer = YouTubeOptimizer()
                
                # Update progress callback
                async def progress_callback(progress: int, message: str):
                    processing_status[video_id] = {
                        "status": "processing",
                        "progress": progress,
                        "message": message,
                        "stage": "optimization"
                    }
                
                # Analyze with optimizer
                processing_status[video_id]["message"] = "Analyzing video with optimizer..."
                analysis_result = await youtube_optimizer.analyze_youtube_video_direct(
                    youtube_url,
                    analysis_options={
                        'include_transcript': True,
                        'extract_moments': True,
                        'extract_sections': True,
                        'enable_visual_search': enable_visual_search
                    },
                    progress_callback=progress_callback
                )
                
                if analysis_result.get("status") == "success":
                    # Update video with analysis results
                    video.transcript = analysis_result.get("transcript", "")
                    video.sections = analysis_result.get("sections", [])
                    
                    # Store visual moments in metadata
                    video.analysis_metadata = {
                        "visual_moments": analysis_result.get("visual_moments", []),
                        "analysis_method": "youtube_optimizer"
                    }
                    
                    # Process key frames if available
                    if "key_frames" in analysis_result:
                        for frame_data in analysis_result["key_frames"]:
                            frame = VideoFrame(
                                video_id=video.id,
                                timestamp=frame_data["timestamp"],
                                frame_path=frame_data.get("frame_path", ""),
                                description=frame_data.get("description", "")
                            )
                            db.add(frame)
                        video.frame_count = len(analysis_result["key_frames"])
                    
                    video.status = "completed"
                    db.commit()
                    
                    processing_status[video_id] = {
                        "status": "completed",
                        "progress": 100,
                        "message": "Video processing completed successfully",
                        "stage": "complete"
                    }
                    
                    logger.info(f"YouTube video {youtube_id} processed successfully with optimizer")
                    return
                
            except Exception as e:
                logger.error(f"Error using YouTube optimizer: {e}")
                # Fall back to standard processing
        
        # Fallback to standard processing
        youtube_service = YouTubeService()
        gemini_service = request.app.state.gemini_service
        video_processor = request.app.state.video_processor
        
        processing_status[video_id]["message"] = "Getting transcript..."
        processing_status[video_id]["progress"] = 20
        
        # Get transcript
        try:
            transcript_data = youtube_service.get_transcript(youtube_id)
            video.transcript = transcript_data["text"]

            # Generate sections using AI
            processing_status[video_id]["message"] = "Generating video sections..."
            processing_status[video_id]["progress"] = 30
            
            video_info = await youtube_service.get_video_info(youtube_id)
            sections = await gemini_service.generate_video_sections(
                transcript_data["text"],
                video_info
            )
            video.sections = sections

        except Exception as e:
            logger.warning(f"Could not get transcript for {youtube_id}: {e}")
            video.transcript = None

        # Download and process the actual video
        try:
            processing_status[video_id]["message"] = "Downloading video..."
            processing_status[video_id]["progress"] = 40
            
            logger.info(f"Downloading YouTube video {youtube_id}...")
            video_path = await youtube_service.download_video(youtube_id, video.id)
            
            if video_path:
                video.file_path = video_path
                
                # Process video to extract frames
                processing_status[video_id]["message"] = "Extracting frames..."
                processing_status[video_id]["progress"] = 60
                
                logger.info(f"Processing downloaded video {youtube_id}...")
                result = await video_processor.process_uploaded_video(video_path, video.id)
                
                if result["status"] == "success":
                    # Save frame information
                    for frame_data in result["frames"]:
                        frame = VideoFrame(
                            video_id=video.id,
                            timestamp=frame_data["timestamp"],
                            frame_path=frame_data["frame_path"]
                        )
                        db.add(frame)
                    
                    video.frame_count = result["frame_count"]
                    video.status = "completed"
                    
                    # Commit frames to database
                    db.commit()
                    
                    # All frame analysis disabled for fast response
                    processing_status[video_id]["message"] = "Processing complete"
                    processing_status[video_id]["progress"] = 100

                    logger.info(f"Frame analysis disabled for video {video.id} - processing complete")
                    
                    # Generate sections if we have transcript
                    if video.transcript:
                        processing_status[video_id]["message"] = "Generating video sections..."
                        processing_status[video_id]["progress"] = 90

                        try:
                            video_info = await youtube_service.get_video_info(youtube_id)
                            sections = await gemini_service.generate_video_sections(
                                video.transcript,
                                video_info
                            )
                            video.sections = sections
                            logger.info(f"Generated {len(sections)} sections for video {video.id}")
                        except Exception as e:
                            logger.error(f"Error generating sections: {e}")
                            video.sections = []

                    # Mark video as completed
                    video.status = "completed"
                else:
                    video.status = "failed"
                    logger.error(f"Failed to process video frames: {result}")
            else:
                # If download fails, still mark as completed if we have transcript
                if video.transcript:
                    video.status = "completed"
                    logger.warning("Video download failed, but transcript is available")
                else:
                    video.status = "failed"
                    logger.error("Both video download and transcript extraction failed")

        except Exception as e:
            logger.error(f"Error processing YouTube video file: {e}")
            # If video processing fails but we have transcript, still mark as completed
            if video.transcript:
                video.status = "completed"
            else:
                video.status = "failed"

        db.commit()
        
        # Update final status
        processing_status[video_id] = {
            "status": video.status,
            "progress": 100 if video.status == "completed" else 0,
            "message": "Processing completed" if video.status == "completed" else "Processing failed",
            "stage": "complete"
        }
        
    except Exception as e:
        logger.error(f"Error in background YouTube processing: {e}")
        processing_status[video_id] = {
            "status": "failed",
            "progress": 0,
            "message": f"Processing failed: {str(e)}",
            "stage": "error"
        }
        
        # Update video status in database
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = "failed"
                db.commit()
        except:
            pass
    finally:
        db.close()


class YouTubeRequest(BaseModel):
    youtube_url: str
    use_optimizer: bool = True  # Use the new YouTube optimizer by default
    enable_visual_search: bool = True  # Enable visual search capabilities

@router.post("/youtube")
async def process_youtube_video(
    request: Request,
    youtube_request: YouTubeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process a YouTube video - returns immediately and processes in background"""
    try:
        youtube_service = YouTubeService()

        # Extract video ID
        video_id = youtube_service.extract_video_id(youtube_request.youtube_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        # Get basic video info (quick operation)
        video_info = await youtube_service.get_video_info(video_id)

        # Create video record immediately
        video = Video(
            title=video_info["title"],
            url=youtube_request.youtube_url,
            video_type="youtube",
            youtube_id=video_id,
            status="processing",
            duration=video_info.get("duration")
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        # Initialize processing status
        processing_status[video.id] = {
            "status": "processing",
            "progress": 0,
            "message": "Starting YouTube video processing...",
            "stage": "initialization"
        }

        # Add background task for processing
        background_tasks.add_task(
            process_youtube_video_background,
            request=request,
            video_id=video.id,
            youtube_id=video_id,
            youtube_url=youtube_request.youtube_url,
            use_optimizer=youtube_request.use_optimizer,
            enable_visual_search=youtube_request.enable_visual_search
        )

        # Return immediately with video ID
        return {
            "video_id": video.id,
            "status": "processing",
            "message": "YouTube video processing started",
            "title": video.title,
            "duration": video.duration,
            "youtube_id": video_id
        }

    except Exception as e:
        logger.error(f"Error initiating YouTube video processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{video_id}/status")
async def get_video_status(video_id: int, db: Session = Depends(get_db)):
    """Get the current processing status of a video"""
    # Check if we have processing status
    if video_id in processing_status:
        status_info = processing_status[video_id].copy()
        
        # Get video from database for additional info
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            status_info.update({
                "video_id": video.id,
                "title": video.title,
                "video_type": video.video_type,
                "duration": video.duration,
                "frame_count": video.frame_count,
                "has_transcript": bool(video.transcript),
                "sections_count": len(video.sections) if video.sections else 0
            })
        
        # Clean up completed/failed statuses after returning
        if status_info["status"] in ["completed", "failed"]:
            # Keep status for 5 minutes after completion
            asyncio.create_task(cleanup_status_after_delay(video_id, 300))
        
        return status_info
    
    # If no processing status, check database
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Return database status
    return {
        "video_id": video.id,
        "status": video.status,
        "progress": 100 if video.status == "completed" else 0,
        "message": f"Video is {video.status}",
        "stage": "complete" if video.status == "completed" else "unknown",
        "title": video.title,
        "video_type": video.video_type,
        "duration": video.duration,
        "frame_count": video.frame_count,
        "has_transcript": bool(video.transcript),
        "sections_count": len(video.sections) if video.sections else 0
    }

async def cleanup_status_after_delay(video_id: int, delay: int):
    """Remove processing status after a delay"""
    await asyncio.sleep(delay)
    if video_id in processing_status:
        del processing_status[video_id]

@router.get("/{video_id}")
async def get_video(video_id: int, db: Session = Depends(get_db)):
    """Get video information"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        "id": video.id,
        "title": video.title,
        "url": video.url,
        "video_type": video.video_type,
        "status": video.status,
        "duration": video.duration,
        "has_transcript": bool(video.transcript),
        "sections": video.sections,
        "frame_count": video.frame_count,
        "created_at": video.created_at
    }

@router.get("/{video_id}/sections")
async def get_video_sections(video_id: int, db: Session = Depends(get_db)):
    """Get video sections"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        "video_id": video.id,
        "sections": video.sections or []
    }

@router.delete("/{video_id}")
async def delete_video(
    request: Request,
    video_id: int,
    db: Session = Depends(get_db)
):
    """Delete a video and its associated files"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        # Clean up files
        video_processor = request.app.state.video_processor
        video_processor.cleanup_video_files(video_id)

        # Delete from database
        db.query(VideoFrame).filter(VideoFrame.video_id == video_id).delete()
        db.delete(video)
        db.commit()

        return {"message": "Video deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting video {video_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


