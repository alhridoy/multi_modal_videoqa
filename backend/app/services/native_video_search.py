import google.generativeai as genai
import logging
import os
import time
import json
import tempfile
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class VideoClip:
    """Represents a video clip with temporal boundaries"""
    start_time: float
    end_time: float
    description: str
    confidence: float
    match_type: str  # exact, partial, related
    visual_elements: List[str]
    context: str
    
    def to_dict(self) -> Dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.end_time - self.start_time,
            "description": self.description,
            "confidence": self.confidence,
            "match_type": self.match_type,
            "visual_elements": self.visual_elements,
            "context": self.context,
            "timestamp_formatted": self._format_timestamp(self.start_time),
            "end_timestamp_formatted": self._format_timestamp(self.end_time)
        }
    
    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS or MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"


class NativeVideoSearchService:
    """
    Advanced video search service using Gemini 2.5's native video understanding.
    Supports object detection, counting, color+object combinations, and temporal queries.
    """
    
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required for native video search")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        self.uploaded_videos: Dict[str, Tuple[str, datetime]] = {}  # video_path -> (file_name, upload_time)
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Clip generation settings
        self.min_clip_duration = 5.0  # seconds
        self.max_clip_duration = 10.0  # seconds
        self.clip_merge_threshold = 3.0  # seconds between clips to merge
        
    async def upload_video(self, video_path: str) -> str:
        """
        Upload video to Gemini and return the file reference.
        Caches uploaded videos to avoid re-uploading.
        """
        try:
            # Check if video is already uploaded and still valid (within 24 hours)
            if video_path in self.uploaded_videos:
                file_name, upload_time = self.uploaded_videos[video_path]
                if datetime.now() - upload_time < timedelta(hours=23):
                    # Verify file still exists in Gemini
                    try:
                        video_file = genai.get_file(file_name)
                        if video_file.state.name == "ACTIVE":
                            logger.info(f"Reusing existing upload: {file_name}")
                            return file_name
                    except:
                        # File no longer exists, remove from cache
                        del self.uploaded_videos[video_path]
            
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            # Upload new video
            logger.info(f"Uploading video to Gemini: {video_path}")
            video_file = genai.upload_file(path=video_path)
            
            # Wait for processing with timeout
            start_time = time.time()
            timeout = 300  # 5 minutes timeout
            
            while video_file.state.name == "PROCESSING":
                if time.time() - start_time > timeout:
                    raise TimeoutError("Video processing timeout exceeded")
                
                logger.info(f"Video processing... ({int(time.time() - start_time)}s)")
                await asyncio.sleep(2)
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name == "FAILED":
                raise Exception("Video processing failed in Gemini")
            
            # Cache the upload
            self.uploaded_videos[video_path] = (video_file.name, datetime.now())
            logger.info(f"Video uploaded successfully: {video_file.name}")
            
            return video_file.name
            
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            raise
    
    async def search_visual_content(self, 
                                  video_path: str, 
                                  query: str,
                                  search_type: str = "general") -> List[VideoClip]:
        """
        Search for visual content in video using Gemini's native understanding.
        
        Args:
            video_path: Path to video file
            query: Search query (e.g., "red car", "person wearing blue")
            search_type: Type of search - general, object, counting, color, text
            
        Returns:
            List of VideoClip objects representing matching segments
        """
        try:
            # Check if video file exists
            if not os.path.exists(video_path):
                logger.error(f"Video file does not exist: {video_path}")
                return []
            
            logger.info(f"Starting native video search for '{query}' (type: {search_type}) on {video_path}")
            
            # Upload video if needed
            video_file_name = await self.upload_video(video_path)
            if not video_file_name:
                logger.error(f"Failed to upload video: {video_path}")
                return []
                
            video_file = genai.get_file(video_file_name)
            logger.info(f"Video file uploaded successfully: {video_file_name}")
            
            # Create search prompt based on type
            prompt = self._create_search_prompt(query, search_type)
            logger.info(f"Generated search prompt length: {len(prompt)} characters")
            
            # Execute search
            logger.info(f"Executing Gemini search for '{query}' (type: {search_type})")
            response = self.model.generate_content([prompt, video_file])
            
            if not response or not response.text:
                logger.error(f"Empty response from Gemini for query: {query}")
                return []
            
            logger.info(f"Received response from Gemini (length: {len(response.text)})")
            
            # Parse results into clips
            clips = self._parse_search_results(response.text, query)
            logger.info(f"Parsed {len(clips)} clips from response")
            
            # Post-process clips (merge nearby, ensure minimum duration)
            if clips:
                clips = self._post_process_clips(clips)
                logger.info(f"Post-processed to {len(clips)} final clips")
            
            logger.info(f"Search completed: Found {len(clips)} clips matching '{query}'")
            return clips

        except Exception as e:
            logger.error(f"Error in visual content search for '{query}': {str(e)}", exc_info=True)
            return []
    
    async def find_all_occurrences(self, video_path: str, visual_element: str) -> List[VideoClip]:
        """
        Find all occurrences of a visual element throughout the video.
        Returns comprehensive list of all appearances.
        """
        try:
            video_file_name = await self.upload_video(video_path)
            video_file = genai.get_file(video_file_name)
            
            prompt = f"""
            COMPREHENSIVE VISUAL SEARCH TASK:
            Find ALL occurrences of "{visual_element}" throughout the entire video.
            
            REQUIREMENTS:
            1. Scan the ENTIRE video from beginning to end
            2. Identify EVERY instance where "{visual_element}" appears
            3. Include partial views, brief appearances, and background occurrences
            4. Note changes in appearance, position, or context
            
            For each occurrence, provide:
            {{
                "start_time": exact seconds when it first appears,
                "end_time": exact seconds when it disappears,
                "description": detailed description of what's shown,
                "confidence": 0.0-1.0 confidence score,
                "visual_details": [list of specific visual attributes],
                "context": what's happening in the scene,
                "prominence": "foreground|background|partial"
            }}
            
            IMPORTANT: 
            - Be exhaustive - don't miss any appearances
            - Include brief glimpses (even 1-2 seconds)
            - Note if the element moves in/out of frame multiple times
            - Consider different angles, distances, or lighting conditions
            
            Return as JSON array. Include timestamps for EVERY appearance.
            """
            
            response = self.model.generate_content([prompt, video_file])
            clips = self._parse_comprehensive_results(response.text, visual_element)
            
            return clips
            
        except Exception as e:
            logger.error(f"Error finding all occurrences: {e}")
            return []
    
    async def count_visual_elements(self, 
                                  video_path: str, 
                                  element: str,
                                  count_type: str = "unique") -> Dict:
        """
        Count occurrences of visual elements in video.
        
        Args:
            video_path: Path to video
            element: What to count (e.g., "cars", "people wearing hats")
            count_type: "unique" (count distinct instances) or "total" (all appearances)
            
        Returns:
            Dictionary with count details and temporal distribution
        """
        try:
            video_file_name = await self.upload_video(video_path)
            video_file = genai.get_file(video_file_name)
            
            prompt = f"""
            VISUAL COUNTING ANALYSIS:
            Count "{element}" in this video.
            
            Counting type: {count_type}
            - "unique": Count distinct/different instances (e.g., 5 different cars)
            - "total": Count all appearances including re-appearances
            
            Provide detailed analysis:
            1. Total count based on counting type
            2. Temporal distribution (when each appears/disappears)
            3. Distinguishing features of each unique instance
            4. Confidence level for each identification
            5. Any ambiguous cases or uncertainties
            
            For each instance found:
            {{
                "instance_id": unique identifier,
                "first_appearance": timestamp in seconds,
                "last_appearance": timestamp in seconds,
                "total_screen_time": duration visible,
                "appearances": [{{start, end}}], // all time ranges when visible
                "description": detailed visual description,
                "distinguishing_features": what makes this instance unique,
                "confidence": 0.0-1.0
            }}
            
            Also provide:
            - total_{count_type}_count: final number
            - temporal_pattern: description of when/how they appear
            - counting_notes: any challenges or ambiguities
            
            Return as structured JSON.
            """
            
            response = self.model.generate_content([prompt, video_file])
            return self._parse_counting_results(response.text, element, count_type)
            
        except Exception as e:
            logger.error(f"Error counting visual elements: {e}")
            return {
                "total_count": 0,
                "count_type": count_type,
                "instances": [],
                "temporal_pattern": "Error occurred",
                "error": str(e)
            }
    
    async def search_color_object_combo(self, 
                                      video_path: str,
                                      color: str,
                                      object_type: str) -> List[VideoClip]:
        """
        Search for specific color + object combinations (e.g., "red car", "blue shirt").
        More precise than general search.
        """
        try:
            video_file_name = await self.upload_video(video_path)
            video_file = genai.get_file(video_file_name)
            
            prompt = f"""
            COLOR + OBJECT VISUAL SEARCH:
            Find all instances of "{color} {object_type}" in the video.
            
            SEARCH CRITERIA:
            1. Color: {color} (consider variations like light/dark {color}, {color}ish tones)
            2. Object: {object_type} (include all types/styles of {object_type})
            3. The {object_type} must prominently feature {color} color
            
            IMPORTANT DISTINCTIONS:
            - A {object_type} that is partially {color} counts
            - A {object_type} in {color} lighting/shadow may count if clearly {color}
            - Multiple {color} {object_type}s in same frame should be noted separately
            
            For each match:
            {{
                "start_time": when the {color} {object_type} appears,
                "end_time": when it disappears,
                "color_accuracy": how well it matches {color} (0.0-1.0),
                "object_confidence": confidence it's a {object_type} (0.0-1.0),
                "description": detailed description,
                "color_details": specific shade/tone of {color},
                "object_details": type/model/style of {object_type},
                "prominence": how prominent in frame,
                "other_colors": any other colors on the {object_type}
            }}
            
            Be precise about color matching. Return JSON array.
            """
            
            response = self.model.generate_content([prompt, video_file])
            clips = self._parse_color_object_results(response.text, color, object_type)
            
            return clips
            
        except Exception as e:
            logger.error(f"Error in color-object search: {e}")
            return []
    
    async def search_text_in_video(self, video_path: str, text_query: str) -> List[VideoClip]:
        """
        Search for text appearing in video (signs, captions, UI elements, etc.)
        """
        try:
            video_file_name = await self.upload_video(video_path)
            video_file = genai.get_file(video_file_name)
            
            prompt = f"""
            TEXT DETECTION AND SEARCH:
            Find all instances of text containing or related to "{text_query}" in the video.
            
            SEARCH SCOPE:
            1. On-screen text overlays and captions
            2. Signs, posters, and written text in the scene
            3. Computer/phone screens with text
            4. Subtitles or closed captions
            5. UI elements with text labels
            6. Any other readable text
            
            MATCHING CRITERIA:
            - Exact matches to "{text_query}"
            - Partial matches containing "{text_query}"
            - Semantically related text (similar meaning)
            
            For each text occurrence:
            {{
                "start_time": when text appears,
                "end_time": when text disappears,
                "text_content": exact text shown,
                "text_type": "caption|sign|screen|subtitle|ui|other",
                "match_type": "exact|partial|semantic",
                "readability": how clearly readable (0.0-1.0),
                "context": what's happening when text appears,
                "position": where on screen (top/bottom/center/etc),
                "relevance_score": how relevant to query (0.0-1.0)
            }}
            
            Return comprehensive JSON array of all text matches.
            """
            
            response = self.model.generate_content([prompt, video_file])
            clips = self._parse_text_search_results(response.text, text_query)
            
            return clips
            
        except Exception as e:
            logger.error(f"Error in text search: {e}")
            return []
    
    async def search_by_scene_type(self, video_path: str, scene_type: str) -> List[VideoClip]:
        """
        Search for specific types of scenes (e.g., "outdoor", "meeting room", "action sequence")
        """
        try:
            video_file_name = await self.upload_video(video_path)
            video_file = genai.get_file(video_file_name)
            
            prompt = f"""
            SCENE TYPE SEARCH:
            Find all segments that match the scene type: "{scene_type}"
            
            SCENE IDENTIFICATION:
            1. Analyze visual composition, setting, and atmosphere
            2. Consider lighting, camera work, and visual style
            3. Identify activities and interactions happening
            4. Note transitions between different scene types
            
            For "{scene_type}" scenes, consider:
            - Physical setting and environment
            - Visual characteristics typical of {scene_type}
            - Activities commonly associated with {scene_type}
            - Mood and atmosphere
            
            For each matching segment:
            {{
                "start_time": when scene begins,
                "end_time": when scene ends,
                "scene_confidence": how well it matches {scene_type} (0.0-1.0),
                "description": detailed scene description,
                "visual_elements": [key visual components],
                "activities": [what's happening],
                "atmosphere": mood/feeling of scene,
                "transitions": how scene begins/ends
            }}
            
            Group continuous {scene_type} content into single clips.
            Return JSON array.
            """
            
            response = self.model.generate_content([prompt, video_file])
            clips = self._parse_scene_search_results(response.text, scene_type)
            
            return clips
            
        except Exception as e:
            logger.error(f"Error in scene type search: {e}")
            return []
    
    async def cleanup_upload(self, video_path: str) -> bool:
        """
        Clean up uploaded video file from Gemini.
        Should be called when done with a video.
        """
        try:
            if video_path in self.uploaded_videos:
                file_name, _ = self.uploaded_videos[video_path]
                genai.delete_file(file_name)
                del self.uploaded_videos[video_path]
                logger.info(f"Cleaned up video upload: {file_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cleaning up video upload: {e}")
            return False
    
    async def cleanup_all_uploads(self) -> int:
        """Clean up all uploaded videos. Returns count of cleaned files."""
        cleaned = 0
        for video_path in list(self.uploaded_videos.keys()):
            if await self.cleanup_upload(video_path):
                cleaned += 1
        return cleaned
    
    def _create_search_prompt(self, query: str, search_type: str) -> str:
        """Create specialized search prompt based on search type"""
        
        # Special handling for people/person queries
        if query.lower() in ['people', 'person', 'human', 'humans', 'individual', 'individuals']:
            return f"""
            TASK: Analyze this video and find all instances where people/humans appear.
            
            DETECTION CRITERIA:
            - Any human beings visible in the video
            - People of any age, gender, or appearance
            - Full body, partial body, or just faces
            - People in foreground or background
            - Include brief appearances and longer presence
            
            ANALYSIS PROCESS:
            1. Scan the entire video from start to finish
            2. Note every moment where any person is visible
            3. Create clips for each distinct appearance or group
            4. Provide precise timestamps for each occurrence
            
            OUTPUT FORMAT (JSON only, no other text):
            [
                {{
                    "start_time": (seconds when person first appears),
                    "end_time": (seconds when person disappears),
                    "confidence": (0.8-1.0 for clear human detection),
                    "description": "Person visible - describe what they're doing",
                    "match_type": "exact",
                    "visual_elements": ["human", "person", "face", "body"],
                    "context": "What's happening in this scene with the person"
                }}
            ]
            
            Be thorough - find every instance where humans are visible, even briefly.
            """
        
        base_prompt = f"""
        You are an advanced video analysis AI. Analyze this video using Gemini 2.5's multimodal understanding capabilities.
        
        SEARCH TASK: Find all instances of "{query}" in this video.
        
        ANALYSIS REQUIREMENTS:
        - Process the video frame by frame at 1 FPS
        - Use both visual and audio cues when relevant
        - Identify temporal moments where "{query}" appears
        - Consider different camera angles, distances, and lighting
        - Look for partial appearances and contextual relevance
        
        For the query "{query}", specifically look for:
        """
        
        type_specific = {
            "object": f"""
            - Objects, items, or entities that match "{query}"
            - Different sizes, orientations, and visual presentations
            - Partial views, occluded instances, or background appearances
            - Consider semantic variations (e.g., "person" includes "man", "woman", "people", "individual")
            """,
            
            "counting": f"""
            - Each distinct instance of "{query}" throughout the video
            - Track appearances, disappearances, and movements
            - Count unique individuals/objects, not repeated frames
            - Note when instances enter/exit the frame
            """,
            
            "color": f"""
            - Items where the specified color is prominent or dominant
            - Consider lighting effects, shadows, and color variations
            - Include objects with the color as a key feature
            - Account for different color saturations and tones
            """,
            
            "text": f"""
            - Written text, signs, captions, or readable content
            - UI elements, labels, or textual information
            - Include partial matches and contextually related text
            - Consider different fonts, sizes, and orientations
            """,
            
            "general": f"""
            - Any visual content related to "{query}"
            - Objects, people, actions, scenes, or concepts
            - Direct matches and semantically related content
            - Consider context and relevance to the search term
            """
        }
        
        format_instruction = f"""
        
        ANALYSIS PROCESS:
        1. Watch the entire video from start to finish
        2. Identify every moment where "{query}" appears
        3. Note the precise timestamps (in seconds) for each occurrence
        4. Create clips that capture the full context of each appearance
        
        OUTPUT FORMAT - Return ONLY a valid JSON array:
        [
            {{
                "start_time": (number in seconds),
                "end_time": (number in seconds),
                "confidence": (0.0 to 1.0),
                "description": "Clear description of what matches '{query}' in this clip",
                "match_type": "exact|partial|related",
                "visual_elements": ["specific", "details", "about", "the", "match"],
                "context": "What's happening in this video segment"
            }}
        ]
        
        REQUIREMENTS:
        - Find ALL instances, even brief appearances
        - Each clip should be 3-15 seconds long
        - Confidence should reflect how well it matches "{query}"
        - Be thorough - don't miss any appearances
        - If no instances found, return empty array: []
        
        RESPOND WITH ONLY THE JSON ARRAY, NO OTHER TEXT.
        """
        
        return base_prompt + type_specific.get(search_type, type_specific["general"]) + format_instruction
    
    def _parse_search_results(self, response_text: str, query: str) -> List[VideoClip]:
        """Parse search results from Gemini response"""
        clips = []
        
        try:
            logger.info(f"Raw response for '{query}': {response_text[:500]}...")
            
            # Clean up the response text
            json_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if "```json" in json_text:
                start = json_text.find("```json") + 7
                end = json_text.find("```", start)
                json_text = json_text[start:end].strip()
            elif "```" in json_text:
                start = json_text.find("```") + 3
                end = json_text.rfind("```")
                if end > start:
                    json_text = json_text[start:end].strip()
            
            # Find JSON array boundaries
            if not json_text.startswith('['):
                start = json_text.find('[')
                if start != -1:
                    end = json_text.rfind(']') + 1
                    if end > start:
                        json_text = json_text[start:end]
                    else:
                        logger.warning(f"Could not find valid JSON array in response")
                        return []
            
            logger.info(f"Extracted JSON: {json_text[:200]}...")
            
            # Parse JSON
            results = json.loads(json_text)
            
            if not isinstance(results, list):
                logger.warning(f"Expected array, got {type(results)}")
                return []
            
            logger.info(f"Parsed {len(results)} results from Gemini response")
            
            # Convert results to VideoClip objects
            for i, item in enumerate(results):
                if isinstance(item, dict):
                    try:
                        clip = VideoClip(
                            start_time=float(item.get("start_time", 0)),
                            end_time=float(item.get("end_time", 0)),
                            description=item.get("description", f"Match {i+1} for '{query}'"),
                            confidence=float(item.get("confidence", 0.5)),
                            match_type=item.get("match_type", "partial"),
                            visual_elements=item.get("visual_elements", []),
                            context=item.get("context", "")
                        )
                        if clip.end_time > clip.start_time and clip.confidence > 0.1:
                            clips.append(clip)
                            logger.info(f"Added clip: {clip.start_time}-{clip.end_time}s, confidence: {clip.confidence}")
                        else:
                            logger.warning(f"Skipped invalid clip: {item}")
                    except Exception as e:
                        logger.error(f"Error creating VideoClip from item {item}: {e}")
                        continue
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON, attempting text parsing")
            # Fallback text parsing
            clips = self._parse_results_from_text(response_text, query)
        
        return clips
    
    def _parse_comprehensive_results(self, response_text: str, element: str) -> List[VideoClip]:
        """Parse comprehensive occurrence search results"""
        clips = []
        
        try:
            # Extract JSON
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            else:
                json_text = response_text
            
            results = json.loads(json_text)
            
            for item in results:
                prominence = item.get("prominence", "foreground")
                confidence_modifier = {
                    "foreground": 1.0,
                    "background": 0.7,
                    "partial": 0.5
                }.get(prominence, 0.8)
                
                clip = VideoClip(
                    start_time=float(item.get("start_time", 0)),
                    end_time=float(item.get("end_time", 0)),
                    description=item.get("description", ""),
                    confidence=float(item.get("confidence", 0.5)) * confidence_modifier,
                    match_type="exact" if prominence == "foreground" else "partial",
                    visual_elements=item.get("visual_details", []),
                    context=item.get("context", "")
                )
                
                if clip.end_time > clip.start_time:
                    clips.append(clip)
                    
        except Exception as e:
            logger.error(f"Error parsing comprehensive results: {e}")
        
        return clips
    
    def _parse_counting_results(self, response_text: str, element: str, count_type: str) -> Dict:
        """Parse counting analysis results"""
        try:
            # Extract JSON
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            else:
                json_text = response_text
            
            data = json.loads(json_text)
            
            # Ensure required fields
            result = {
                "total_count": data.get(f"total_{count_type}_count", 0),
                "count_type": count_type,
                "element": element,
                "instances": data.get("instances", []),
                "temporal_pattern": data.get("temporal_pattern", ""),
                "counting_notes": data.get("counting_notes", ""),
                "confidence": data.get("overall_confidence", 0.8)
            }
            
            # Convert instance appearances to clips
            clips = []
            for instance in result["instances"]:
                for appearance in instance.get("appearances", []):
                    clip = VideoClip(
                        start_time=appearance.get("start", 0),
                        end_time=appearance.get("end", 0),
                        description=instance.get("description", ""),
                        confidence=instance.get("confidence", 0.8),
                        match_type="exact",
                        visual_elements=instance.get("distinguishing_features", []),
                        context=f"Instance {instance.get('instance_id', 'unknown')}"
                    )
                    clips.append(clip)
            
            result["clips"] = [clip.to_dict() for clip in clips]
            return result
            
        except Exception as e:
            logger.error(f"Error parsing counting results: {e}")
            return {
                "total_count": 0,
                "count_type": count_type,
                "element": element,
                "instances": [],
                "error": str(e)
            }
    
    def _parse_color_object_results(self, response_text: str, color: str, object_type: str) -> List[VideoClip]:
        """Parse color+object search results"""
        clips = []
        
        try:
            # Extract JSON
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            else:
                json_text = response_text
            
            results = json.loads(json_text)
            
            for item in results:
                # Calculate combined confidence
                color_acc = float(item.get("color_accuracy", 0.5))
                obj_conf = float(item.get("object_confidence", 0.5))
                combined_confidence = (color_acc + obj_conf) / 2
                
                # Determine match type based on confidences
                if color_acc > 0.8 and obj_conf > 0.8:
                    match_type = "exact"
                elif color_acc > 0.6 and obj_conf > 0.6:
                    match_type = "partial"
                else:
                    match_type = "related"
                
                clip = VideoClip(
                    start_time=float(item.get("start_time", 0)),
                    end_time=float(item.get("end_time", 0)),
                    description=item.get("description", f"{color} {object_type}"),
                    confidence=combined_confidence,
                    match_type=match_type,
                    visual_elements=[
                        f"Color: {item.get('color_details', color)}",
                        f"Object: {item.get('object_details', object_type)}",
                        f"Prominence: {item.get('prominence', 'medium')}"
                    ],
                    context=item.get("context", "")
                )
                
                if clip.end_time > clip.start_time:
                    clips.append(clip)
                    
        except Exception as e:
            logger.error(f"Error parsing color-object results: {e}")
        
        return clips
    
    def _parse_text_search_results(self, response_text: str, text_query: str) -> List[VideoClip]:
        """Parse text search results"""
        clips = []
        
        try:
            # Extract JSON
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            else:
                json_text = response_text
            
            results = json.loads(json_text)
            
            for item in results:
                # Use relevance and readability for confidence
                relevance = float(item.get("relevance_score", 0.5))
                readability = float(item.get("readability", 0.5))
                confidence = (relevance + readability) / 2
                
                clip = VideoClip(
                    start_time=float(item.get("start_time", 0)),
                    end_time=float(item.get("end_time", 0)),
                    description=f"Text: '{item.get('text_content', '')}' - {item.get('text_type', 'unknown')} text",
                    confidence=confidence,
                    match_type=item.get("match_type", "partial"),
                    visual_elements=[
                        f"Position: {item.get('position', 'unknown')}",
                        f"Type: {item.get('text_type', 'unknown')}",
                        f"Readability: {readability:.1%}"
                    ],
                    context=item.get("context", "")
                )
                
                if clip.end_time > clip.start_time:
                    clips.append(clip)
                    
        except Exception as e:
            logger.error(f"Error parsing text search results: {e}")
        
        return clips
    
    def _parse_scene_search_results(self, response_text: str, scene_type: str) -> List[VideoClip]:
        """Parse scene type search results"""
        clips = []
        
        try:
            # Extract JSON
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            else:
                json_text = response_text
            
            results = json.loads(json_text)
            
            for item in results:
                clip = VideoClip(
                    start_time=float(item.get("start_time", 0)),
                    end_time=float(item.get("end_time", 0)),
                    description=item.get("description", f"{scene_type} scene"),
                    confidence=float(item.get("scene_confidence", 0.5)),
                    match_type="exact" if item.get("scene_confidence", 0) > 0.8 else "partial",
                    visual_elements=item.get("visual_elements", []),
                    context=f"{item.get('atmosphere', '')} - {', '.join(item.get('activities', []))}"
                )
                
                if clip.end_time > clip.start_time:
                    clips.append(clip)
                    
        except Exception as e:
            logger.error(f"Error parsing scene search results: {e}")
        
        return clips
    
    def _parse_results_from_text(self, text: str, query: str) -> List[VideoClip]:
        """Fallback text parser for results"""
        clips = []
        
        # Simple pattern matching for timestamps
        import re
        
        # Look for patterns like "0:00-0:10" or "5.5s to 10.2s"
        time_patterns = [
            r'(\d+:\d+)\s*[-–]\s*(\d+:\d+)',
            r'(\d+\.?\d*)\s*s\s*to\s*(\d+\.?\d*)\s*s',
            r'from\s*(\d+\.?\d*)\s*to\s*(\d+\.?\d*)',
        ]
        
        lines = text.split('\n')
        
        for line in lines:
            for pattern in time_patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        # Convert to seconds
                        start = match.group(1)
                        end = match.group(2)
                        
                        if ':' in start:
                            parts = start.split(':')
                            start_seconds = int(parts[0]) * 60 + int(parts[1])
                        else:
                            start_seconds = float(start)
                        
                        if ':' in end:
                            parts = end.split(':')
                            end_seconds = int(parts[0]) * 60 + int(parts[1])
                        else:
                            end_seconds = float(end)
                        
                        clip = VideoClip(
                            start_time=start_seconds,
                            end_time=end_seconds,
                            description=line,
                            confidence=0.5,
                            match_type="partial",
                            visual_elements=[query],
                            context=""
                        )
                        
                        clips.append(clip)
                        break
                        
                    except:
                        continue
        
        return clips
    
    def _post_process_clips(self, clips: List[VideoClip]) -> List[VideoClip]:
        """Post-process clips to merge nearby ones and ensure minimum duration"""
        if not clips:
            return clips
        
        # Sort by start time
        clips.sort(key=lambda x: x.start_time)
        
        processed = []
        current_clip = None
        
        for clip in clips:
            if current_clip is None:
                current_clip = clip
            elif clip.start_time - current_clip.end_time <= self.clip_merge_threshold:
                # Merge clips
                current_clip = VideoClip(
                    start_time=current_clip.start_time,
                    end_time=max(clip.end_time, current_clip.end_time),
                    description=f"{current_clip.description} ... {clip.description}",
                    confidence=max(current_clip.confidence, clip.confidence),
                    match_type=current_clip.match_type if current_clip.confidence >= clip.confidence else clip.match_type,
                    visual_elements=list(set(current_clip.visual_elements + clip.visual_elements)),
                    context=f"{current_clip.context} {clip.context}".strip()
                )
            else:
                # Ensure minimum duration
                if current_clip.end_time - current_clip.start_time < self.min_clip_duration:
                    current_clip.end_time = min(
                        current_clip.start_time + self.min_clip_duration,
                        clip.start_time - 0.1  # Don't overlap with next clip
                    )
                processed.append(current_clip)
                current_clip = clip
        
        # Handle last clip
        if current_clip:
            if current_clip.end_time - current_clip.start_time < self.min_clip_duration:
                current_clip.end_time = current_clip.start_time + self.min_clip_duration
            processed.append(current_clip)
        
        return processed


# Convenience functions for different search types
async def search_objects(video_path: str, object_query: str) -> List[Dict]:
    """Search for specific objects in video"""
    service = NativeVideoSearchService()
    clips = await service.search_visual_content(video_path, object_query, "object")
    return [clip.to_dict() for clip in clips]


async def count_occurrences(video_path: str, element: str, unique_only: bool = True) -> Dict:
    """Count occurrences of visual elements"""
    service = NativeVideoSearchService()
    return await service.count_visual_elements(
        video_path, 
        element, 
        "unique" if unique_only else "total"
    )


async def find_color_objects(video_path: str, color: str, object_type: str) -> List[Dict]:
    """Find objects of specific color"""
    service = NativeVideoSearchService()
    clips = await service.search_color_object_combo(video_path, color, object_type)
    return [clip.to_dict() for clip in clips]


async def find_text(video_path: str, text: str) -> List[Dict]:
    """Find text in video"""
    service = NativeVideoSearchService()
    clips = await service.search_text_in_video(video_path, text)
    return [clip.to_dict() for clip in clips]


async def find_scenes(video_path: str, scene_type: str) -> List[Dict]:
    """Find specific types of scenes"""
    service = NativeVideoSearchService()
    clips = await service.search_by_scene_type(video_path, scene_type)
    return [clip.to_dict() for clip in clips]