"""
Thumbnail Service for generating and serving real video thumbnails
Supports multiple sizes and formats for optimal UX
"""

import logging
import os
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import hashlib
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ThumbnailSpec:
    """Specification for thumbnail generation"""
    width: int
    height: int
    quality: int = 85
    format: str = 'JPEG'
    suffix: str = ''

class ThumbnailService:
    """Service for generating and managing video thumbnails"""
    
    def __init__(self, thumbnail_dir: str = "./thumbnails"):
        self.thumbnail_dir = Path(thumbnail_dir)
        self.thumbnail_dir.mkdir(exist_ok=True)
        
        # Thumbnail specifications for different use cases
        self.specs = {
            'small': ThumbnailSpec(120, 68, 80, 'JPEG', '_small'),      # Search results
            'medium': ThumbnailSpec(240, 135, 85, 'JPEG', '_medium'),   # Timeline markers
            'large': ThumbnailSpec(480, 270, 90, 'JPEG', '_large'),     # Preview/hover
            'timeline': ThumbnailSpec(160, 90, 80, 'JPEG', '_timeline') # Timeline scrubbing
        }
        
        # Cache for generated thumbnails
        self.thumbnail_cache = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load thumbnail cache from disk"""
        cache_file = self.thumbnail_dir / "thumbnail_cache.json"
        try:
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    self.thumbnail_cache = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load thumbnail cache: {e}")
            self.thumbnail_cache = {}
    
    def _save_cache(self):
        """Save thumbnail cache to disk"""
        cache_file = self.thumbnail_dir / "thumbnail_cache.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(self.thumbnail_cache, f)
        except Exception as e:
            logger.warning(f"Could not save thumbnail cache: {e}")
    
    def _get_cache_key(self, video_path: str, timestamp: float, spec_name: str) -> str:
        """Generate cache key for thumbnail"""
        key_data = f"{video_path}:{timestamp}:{spec_name}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _extract_frame_at_timestamp(self, video_path: str, timestamp: float) -> Optional[np.ndarray]:
        """Extract frame from video at specific timestamp"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return None
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            # Ensure timestamp is within video duration
            timestamp = max(0, min(timestamp, duration - 0.1))
            
            # Seek to timestamp
            frame_number = int(timestamp * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Read frame
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                return frame
            else:
                logger.warning(f"Could not read frame at timestamp {timestamp} from {video_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting frame: {e}")
            return None
    
    def _resize_frame(self, frame: np.ndarray, spec: ThumbnailSpec) -> np.ndarray:
        """Resize frame according to thumbnail specification"""
        try:
            # Calculate aspect ratio preserving resize
            h, w = frame.shape[:2]
            aspect_ratio = w / h
            target_aspect = spec.width / spec.height
            
            if aspect_ratio > target_aspect:
                # Video is wider, fit to width
                new_width = spec.width
                new_height = int(spec.width / aspect_ratio)
            else:
                # Video is taller, fit to height
                new_height = spec.height
                new_width = int(spec.height * aspect_ratio)
            
            # Resize frame
            resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Create canvas with target size
            canvas = np.zeros((spec.height, spec.width, 3), dtype=np.uint8)
            
            # Center the resized frame on canvas
            y_offset = (spec.height - new_height) // 2
            x_offset = (spec.width - new_width) // 2
            canvas[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = resized
            
            return canvas
            
        except Exception as e:
            logger.error(f"Error resizing frame: {e}")
            return frame
    
    def _add_timestamp_overlay(self, frame: np.ndarray, timestamp: float, spec: ThumbnailSpec) -> np.ndarray:
        """Add timestamp overlay to thumbnail"""
        try:
            # Convert to PIL for text rendering
            pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_image)
            
            # Format timestamp
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            time_text = f"{minutes}:{seconds:02d}"
            
            # Calculate font size based on thumbnail size
            font_size = max(10, spec.width // 20)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # Get text size
            bbox = draw.textbbox((0, 0), time_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Position in bottom-right corner with padding
            padding = 4
            x = spec.width - text_width - padding
            y = spec.height - text_height - padding
            
            # Draw background rectangle
            draw.rectangle([x-2, y-2, x+text_width+2, y+text_height+2], fill=(0, 0, 0, 180))
            
            # Draw text
            draw.text((x, y), time_text, fill=(255, 255, 255), font=font)
            
            # Convert back to OpenCV format
            return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            logger.warning(f"Could not add timestamp overlay: {e}")
            return frame
    
    def generate_thumbnail(self, video_path: str, timestamp: float, 
                          spec_name: str = 'medium', add_timestamp: bool = True) -> Optional[str]:
        """Generate thumbnail for video at specific timestamp"""
        try:
            if spec_name not in self.specs:
                logger.error(f"Unknown thumbnail spec: {spec_name}")
                return None
            
            spec = self.specs[spec_name]
            cache_key = self._get_cache_key(video_path, timestamp, spec_name)
            
            # Check cache first
            if cache_key in self.thumbnail_cache:
                thumbnail_path = self.thumbnail_cache[cache_key]
                if os.path.exists(thumbnail_path):
                    return thumbnail_path
            
            # Extract frame from video
            frame = self._extract_frame_at_timestamp(video_path, timestamp)
            if frame is None:
                return None
            
            # Resize frame
            resized_frame = self._resize_frame(frame, spec)
            
            # Add timestamp overlay if requested
            if add_timestamp:
                resized_frame = self._add_timestamp_overlay(resized_frame, timestamp, spec)
            
            # Generate thumbnail filename
            video_name = Path(video_path).stem
            timestamp_str = f"{timestamp:.1f}".replace('.', '_')
            thumbnail_filename = f"{video_name}_{timestamp_str}{spec.suffix}.{spec.format.lower()}"
            thumbnail_path = self.thumbnail_dir / thumbnail_filename
            
            # Save thumbnail
            if spec.format.upper() == 'JPEG':
                cv2.imwrite(str(thumbnail_path), resized_frame, 
                           [cv2.IMWRITE_JPEG_QUALITY, spec.quality])
            else:
                cv2.imwrite(str(thumbnail_path), resized_frame)
            
            # Update cache
            self.thumbnail_cache[cache_key] = str(thumbnail_path)
            self._save_cache()
            
            return str(thumbnail_path)
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return None
    
    def generate_timeline_thumbnails(self, video_path: str, interval: float = 10.0) -> List[Dict]:
        """Generate thumbnails for video timeline at regular intervals"""
        try:
            # Get video duration
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return []
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            cap.release()
            
            # Generate thumbnails at intervals
            thumbnails = []
            timestamp = 0
            
            while timestamp < duration:
                thumbnail_path = self.generate_thumbnail(
                    video_path, timestamp, 'timeline', add_timestamp=True
                )
                
                if thumbnail_path:
                    thumbnails.append({
                        'timestamp': timestamp,
                        'thumbnail_path': thumbnail_path,
                        'url': f"/api/thumbnails/{Path(thumbnail_path).name}"
                    })
                
                timestamp += interval
            
            logger.info(f"Generated {len(thumbnails)} timeline thumbnails for {video_path}")
            return thumbnails
            
        except Exception as e:
            logger.error(f"Error generating timeline thumbnails: {e}")
            return []
    
    def generate_search_result_thumbnails(self, video_path: str, timestamps: List[float]) -> Dict[float, str]:
        """Generate thumbnails for search results"""
        thumbnails = {}
        
        for timestamp in timestamps:
            thumbnail_path = self.generate_thumbnail(
                video_path, timestamp, 'small', add_timestamp=True
            )
            
            if thumbnail_path:
                thumbnails[timestamp] = f"/api/thumbnails/{Path(thumbnail_path).name}"
        
        return thumbnails
    
    def cleanup_old_thumbnails(self, max_age_days: int = 7):
        """Clean up old thumbnail files"""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            removed_count = 0
            for thumbnail_file in self.thumbnail_dir.glob("*.jpg"):
                if current_time - thumbnail_file.stat().st_mtime > max_age_seconds:
                    thumbnail_file.unlink()
                    removed_count += 1
            
            # Clean up cache entries for removed files
            self.thumbnail_cache = {
                k: v for k, v in self.thumbnail_cache.items() 
                if os.path.exists(v)
            }
            self._save_cache()
            
            logger.info(f"Cleaned up {removed_count} old thumbnails")
            
        except Exception as e:
            logger.error(f"Error cleaning up thumbnails: {e}")
    
    def get_thumbnail_stats(self) -> Dict:
        """Get thumbnail service statistics"""
        try:
            thumbnail_count = len(list(self.thumbnail_dir.glob("*.jpg")))
            cache_size = len(self.thumbnail_cache)
            
            # Calculate total size
            total_size = sum(
                f.stat().st_size for f in self.thumbnail_dir.glob("*") 
                if f.is_file()
            )
            
            return {
                "thumbnail_count": thumbnail_count,
                "cache_entries": cache_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "thumbnail_dir": str(self.thumbnail_dir),
                "specs": {name: f"{spec.width}x{spec.height}" for name, spec in self.specs.items()}
            }
            
        except Exception as e:
            logger.error(f"Error getting thumbnail stats: {e}")
            return {"error": str(e)}
