import cv2
import os
import logging
from typing import List, Dict, Optional
import numpy as np
from PIL import Image
import tempfile
import subprocess
from app.core.config import settings

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Service for processing video files and extracting frames"""
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.frame_interval = settings.FRAME_EXTRACTION_INTERVAL
        
        # Create upload directory if it doesn't exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(f"{self.upload_dir}/frames", exist_ok=True)
    
    async def process_uploaded_video(self, file_path: str, video_id: int) -> Dict:
        """Process an uploaded video file"""
        try:
            # Get video information
            video_info = self._get_video_info(file_path)
            
            # Extract frames
            frames = await self._extract_frames(file_path, video_id)
            
            return {
                "status": "success",
                "video_info": video_info,
                "frames": frames,
                "frame_count": len(frames)
            }
            
        except Exception as e:
            logger.error(f"Error processing video {video_id}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "frames": [],
                "frame_count": 0
            }
    
    async def download_youtube_video(self, video_url: str, video_id: int) -> Optional[str]:
        """Download YouTube video for processing using yt-dlp"""
        try:
            import yt_dlp
            import asyncio
            import os

            output_path = f"{self.upload_dir}/video_{video_id}.%(ext)s"
            final_path = f"{self.upload_dir}/video_{video_id}.mp4"

            # yt-dlp options
            ydl_opts = {
                'format': 'best[height<=720]/best',  # Limit to 720p for processing efficiency
                'outtmpl': output_path,
                'noplaylist': True,
                'extract_flat': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': True,
                'no_warnings': True,
                'quiet': True,
            }

            def download_video():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])

                    # Find the downloaded file
                    for file in os.listdir(self.upload_dir):
                        if file.startswith(f"video_{video_id}.") and file.endswith(('.mp4', '.webm', '.mkv')):
                            downloaded_path = os.path.join(self.upload_dir, file)

                            # If it's not mp4, we'll keep the original format for now
                            if not file.endswith('.mp4'):
                                final_path = downloaded_path
                            else:
                                final_path = downloaded_path

                            return final_path
                    return None

            # Run download in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, download_video)

            if result and os.path.exists(result):
                logger.info(f"Successfully downloaded YouTube video: {video_url} -> {result}")
                return result
            else:
                logger.error(f"Failed to download YouTube video: {video_url}")
                return None

        except ImportError:
            logger.error("yt-dlp not installed. Cannot download YouTube videos.")
            return None
        except Exception as e:
            logger.error(f"Error downloading YouTube video: {e}")
            return None
    
    async def _extract_frames(self, video_path: str, video_id: int) -> List[Dict]:
        """Extract frames from video at regular intervals"""
        frames = []
        
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                raise Exception("Could not open video file")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            frame_interval_frames = int(fps * self.frame_interval)
            frame_count = 0
            extracted_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Extract frame at intervals
                if frame_count % frame_interval_frames == 0:
                    timestamp = frame_count / fps
                    
                    # Save frame
                    frame_filename = f"video_{video_id}_frame_{extracted_count}_{int(timestamp)}.jpg"
                    frame_path = f"{self.upload_dir}/frames/{frame_filename}"
                    
                    # Convert BGR to RGB, resize for efficiency, and save
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = Image.fromarray(frame_rgb)
                    # Resize to 640x360 for efficiency while maintaining quality
                    image = image.resize((640, 360), Image.Resampling.LANCZOS)
                    image.save(frame_path, "JPEG", quality=85, optimize=True)
                    
                    frames.append({
                        "timestamp": timestamp,
                        "frame_path": frame_path,
                        "frame_number": extracted_count
                    })
                    
                    extracted_count += 1
                
                frame_count += 1
            
            cap.release()
            
            logger.info(f"Extracted {len(frames)} frames from video {video_id}")
            return frames
            
        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
            return []
    
    def _get_video_info(self, video_path: str) -> Dict:
        """Get video metadata"""
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                raise Exception("Could not open video file")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = total_frames / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                "duration": duration,
                "fps": fps,
                "total_frames": total_frames,
                "width": width,
                "height": height,
                "size_mb": os.path.getsize(video_path) / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {}
    
    def cleanup_video_files(self, video_id: int):
        """Clean up video and frame files"""
        try:
            # Remove video file
            video_path = f"{self.upload_dir}/video_{video_id}.mp4"
            if os.path.exists(video_path):
                os.remove(video_path)
            
            # Remove frame files
            frames_dir = f"{self.upload_dir}/frames"
            for filename in os.listdir(frames_dir):
                if filename.startswith(f"video_{video_id}_"):
                    os.remove(os.path.join(frames_dir, filename))
            
            logger.info(f"Cleaned up files for video {video_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up video files: {e}")
    
    def get_frame_at_timestamp(self, video_path: str, timestamp: float) -> Optional[str]:
        """Extract a specific frame at given timestamp"""
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return None
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_number = int(timestamp * fps)
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if ret:
                # Save frame to temporary file with optimization
                temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame_rgb)
                # Resize for efficiency
                image = image.resize((640, 360), Image.Resampling.LANCZOS)
                image.save(temp_file.name, "JPEG", quality=85, optimize=True)
                
                cap.release()
                return temp_file.name
            
            cap.release()
            return None
            
        except Exception as e:
            logger.error(f"Error extracting frame at timestamp {timestamp}: {e}")
            return None
