import re
import logging
import os
import subprocess
import asyncio
from typing import Optional, Dict, List
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class YouTubeService:
    """Service for handling YouTube video operations"""
    
    def __init__(self):
        self.formatter = TextFormatter()
        self.download_dir = os.path.join(settings.UPLOAD_DIR, 'youtube')
        os.makedirs(self.download_dir, exist_ok=True)
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def get_video_info(self, video_id: str) -> Dict:
        """Get video information using yt-dlp"""
        try:
            # Use yt-dlp to get video info without downloading
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-download',
                f'https://www.youtube.com/watch?v={video_id}'
            ]
            
            # Use async subprocess to avoid blocking
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            result = type('Result', (), {
                'returncode': process.returncode,
                'stdout': stdout.decode(),
                'stderr': stderr.decode()
            })()
            
            if result.returncode == 0:
                import json
                video_info = json.loads(result.stdout)
                
                return {
                    "id": video_id,
                    "title": video_info.get('title', f'YouTube Video {video_id}'),
                    "duration": video_info.get('duration', 0),
                    "description": video_info.get('description', ''),
                    "thumbnail": video_info.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"),
                    "uploader": video_info.get('uploader', 'Unknown'),
                    "view_count": video_info.get('view_count', 0)
                }
            else:
                # Fallback to basic info
                return {
                    "id": video_id,
                    "title": f"YouTube Video {video_id}",
                    "duration": None,
                    "description": "",
                    "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                }
                
        except Exception as e:
            logger.error(f"Error getting video info for {video_id}: {e}")
            # Return fallback info
            return {
                "id": video_id,
                "title": f"YouTube Video {video_id}",
                "duration": None,
                "description": "",
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            }
    
    async def download_video(self, video_id: str, video_db_id: int) -> Optional[str]:
        """Download YouTube video using yt-dlp"""
        try:
            output_path = os.path.join(self.download_dir, f'video_{video_db_id}.mp4')
            
            # Check if yt-dlp is available
            if not await self._check_ytdlp_available():
                logger.error("yt-dlp is not installed. Please install it with: pip install yt-dlp")
                return None
            
            # Download video with yt-dlp
            cmd = [
                'yt-dlp',
                '-f', 'best[ext=mp4][height<=720]/best[height<=720]/best',  # Limit to 720p for faster processing
                '-o', output_path,
                '--no-playlist',
                '--quiet',
                '--no-warnings',
                f'https://www.youtube.com/watch?v={video_id}'
            ]
            
            logger.info(f"Downloading YouTube video {video_id}...")
            # Use async subprocess to avoid blocking
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            result = type('Result', (), {
                'returncode': process.returncode,
                'stdout': stdout.decode(),
                'stderr': stderr.decode()
            })()
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Successfully downloaded video to {output_path}")
                return output_path
            else:
                logger.error(f"Failed to download video: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading YouTube video {video_id}: {e}")
            return None
    
    async def _check_ytdlp_available(self) -> bool:
        """Check if yt-dlp is available"""
        try:
            process = await asyncio.create_subprocess_exec(
                'yt-dlp', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except:
            return False
    
    def get_transcript(self, video_id: str, languages: List[str] = None) -> Dict:
        """Get video transcript"""
        if languages is None:
            languages = ['en', 'en-US', 'en-GB']
        
        try:
            # Try to get transcript in preferred languages
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # First try manually created transcripts
            for lang in languages:
                try:
                    transcript = transcript_list.find_manually_created_transcript([lang])
                    transcript_data = transcript.fetch()
                    
                    return {
                        "transcript": transcript_data,
                        "text": self.formatter.format_transcript(transcript_data),
                        "language": lang,
                        "type": "manual"
                    }
                except:
                    continue
            
            # Then try auto-generated transcripts
            for lang in languages:
                try:
                    transcript = transcript_list.find_generated_transcript([lang])
                    transcript_data = transcript.fetch()
                    
                    return {
                        "transcript": transcript_data,
                        "text": self.formatter.format_transcript(transcript_data),
                        "language": lang,
                        "type": "auto"
                    }
                except:
                    continue
            
            # If no transcript found in preferred languages, get any available
            try:
                transcript = transcript_list.find_transcript(['en'])
                transcript_data = transcript.fetch()
                
                return {
                    "transcript": transcript_data,
                    "text": self.formatter.format_transcript(transcript_data),
                    "language": "en",
                    "type": "fallback"
                }
            except:
                pass
            
            raise Exception("No transcript available")
            
        except Exception as e:
            logger.error(f"Error getting transcript for {video_id}: {e}")
            raise
    
    def generate_sections_from_transcript(self, transcript_data: List[Dict]) -> List[Dict]:
        """Generate video sections from transcript data"""
        if not transcript_data:
            return []
        
        sections = []
        current_section = None
        section_duration = 60  # 1 minute sections
        
        for entry in transcript_data:
            start_time = entry['start']
            text = entry['text']
            
            # Create new section if needed
            if current_section is None or start_time - current_section['start_time'] > section_duration:
                if current_section:
                    current_section['end_time'] = start_time
                    sections.append(current_section)
                
                current_section = {
                    'id': len(sections) + 1,
                    'title': self._generate_section_title(text),
                    'start_time': start_time,
                    'end_time': start_time + section_duration,
                    'description': text[:100] + "..." if len(text) > 100 else text,
                    'key_topics': self._extract_key_topics(text)
                }
            else:
                # Add to current section
                current_section['description'] += " " + text
                current_section['key_topics'].extend(self._extract_key_topics(text))
        
        # Add final section
        if current_section:
            current_section['end_time'] = transcript_data[-1]['start'] + transcript_data[-1].get('duration', 5)
            sections.append(current_section)
        
        return sections
    
    def _generate_section_title(self, text: str) -> str:
        """Generate a title for a section based on text content"""
        # Simple title generation - in production, use NLP
        words = text.split()[:5]
        return " ".join(words).title()
    
    def _extract_key_topics(self, text: str) -> List[str]:
        """Extract key topics from text"""
        # Simple keyword extraction - in production, use NLP
        common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'a', 'an'}
        
        words = [word.lower().strip('.,!?;:') for word in text.split()]
        keywords = [word for word in words if len(word) > 3 and word not in common_words]
        
        return list(set(keywords[:3]))  # Return top 3 unique keywords
