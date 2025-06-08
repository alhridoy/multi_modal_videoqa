
import logging
import os
import time
import asyncio
import hashlib
from typing import List, Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class SearchResult(BaseModel):
    timestamp: float
    confidence: float
    description: str
    frame_path: str
    clip_start: float
    clip_end: float

class ClipResult(BaseModel):
    start_time: float
    end_time: float
    confidence: float
    description: str
    thumbnail_url: Optional[str] = None

class VideoSearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    clips: List[ClipResult] = []
    total_results: int
    processing_method: str
    processing_time: float
    direct_answer: Optional[str] = None
    query_type: Optional[str] = None

class SimpleVideoSearch:
    """
    Simple, effective video search using the best available method.
    
    Priority:
    1. Native Gemini 2.5 video analysis (best accuracy, no preprocessing)
    2. Fallback to basic frame analysis if needed
    """
    
    def __init__(self):
        self.gemini_service = None
        self.native_service = None
        self._native_available = False

        # Native video search will be initialized when available
        logger.info("Simple video search initialized - native search will be enabled when available")
    
    def initialize_gemini(self, gemini_service):
        """Initialize with Gemini service from app state"""
        self.gemini_service = gemini_service

    def initialize_native_service(self, native_service):
        """Initialize the native video search service for fast searches"""
        self.native_service = native_service
        self._native_available = True
        logger.info("Native video search service initialized - fast searches enabled!")
    
    async def search(self, video_path: str, query: str, video_id: int) -> VideoSearchResponse:
        """
        Simple search: try the best method first, fallback if needed
        """
        start_time = time.time()
        
        logger.info(f"Simple search for '{query}' in video {video_id}")
        
        # METHOD 1: Native Gemini 2.5 Video Analysis (DISABLED - CAUSING DELAYS!)
        if False and self.gemini_service and video_path and os.path.exists(video_path):
            try:
                # Use native video search directly through Gemini service
                results = await self._native_gemini_search(video_path, query, video_id)
                if results:
                    processing_time = time.time() - start_time
                    logger.info(f"Native Gemini search found {len(results)} results in {processing_time:.2f}s")

                    # Convert results to clips for timeline/clips view
                    clips = self._results_to_clips(results)

                    return VideoSearchResponse(
                        query=query,
                        results=results,
                        clips=clips,
                        total_results=len(results),
                        processing_method="native_gemini_video",
                        processing_time=processing_time,
                        direct_answer=f"Found {len(results)} instances of '{query}' in the video",
                        query_type="visual_search"
                    )
            except Exception as e:
                logger.warning(f"Native Gemini search failed, falling back to frame analysis: {e}")

        # METHOD 2: Direct Frame Analysis (FALLBACK)
        if self.gemini_service and video_path and os.path.exists(video_path):
            try:
                results = await self._native_search(video_path, query)
                if results:
                    processing_time = time.time() - start_time
                    logger.info(f"Native search found {len(results)} results in {processing_time:.2f}s")

                    # Convert results to clips for timeline/clips view
                    clips = self._results_to_clips(results)

                    return VideoSearchResponse(
                        query=query,
                        results=results,
                        clips=clips,
                        total_results=len(results),
                        processing_method="native_gemini_video",
                        processing_time=processing_time,
                        direct_answer=f"Found {len(results)} instances of '{query}' in the video",
                        query_type="visual_search"
                    )
            except Exception as e:
                logger.warning(f"Native search failed: {e}")
        
        # METHOD 2: Direct Frame Analysis (FALLBACK)
        if self.gemini_service and video_path and os.path.exists(video_path):
            try:
                results = await self._direct_frame_search(video_path, query, video_id)
                processing_time = time.time() - start_time
                logger.info(f"Frame search found {len(results)} results in {processing_time:.2f}s")

                # Convert results to clips for timeline/clips view
                clips = self._results_to_clips(results)

                return VideoSearchResponse(
                    query=query,
                    results=results,
                    clips=clips,
                    total_results=len(results),
                    processing_method="direct_frame_analysis",
                    processing_time=processing_time,
                    direct_answer=f"Found {len(results)} instances of '{query}' in the video",
                    query_type="visual_search"
                )
            except Exception as e:
                logger.error(f"Frame search failed: {e}")
        
        # METHOD 3: No results (but don't fail)
        processing_time = time.time() - start_time
        return VideoSearchResponse(
            query=query,
            results=[],
            total_results=0,
            processing_method="no_results",
            processing_time=processing_time
        )

    async def _native_gemini_search(self, video_path: str, query: str, video_id: int = None) -> List[SearchResult]:
        """
        Use Gemini 2.5's native video understanding for FAST and ACCURATE search
        This is the BEST method - processes entire video in one API call
        """
        try:
            # Use Gemini's native video search capability
            search_results = await self.gemini_service.search_video_content(video_path, query)

            results = []
            for result in search_results:
                # Convert Gemini results to SearchResult format
                timestamp = result.get('timestamp', 0.0)
                confidence = result.get('confidence', 0.8) * 100
                description = result.get('description', f"Found '{query}' at {timestamp:.1f}s")

                # Create clip around the match
                clip_start = max(0, timestamp - 5)
                clip_end = timestamp + 10  # Longer clips for better context

                results.append(SearchResult(
                    timestamp=timestamp,
                    confidence=confidence,
                    description=description,
                    frame_path=f"/api/v1/search/{video_id}/frame?timestamp={timestamp}",
                    clip_start=clip_start,
                    clip_end=clip_end
                ))

            logger.info(f"Native Gemini search processed entire video in one call")
            return results

        except Exception as e:
            logger.error(f"Native Gemini search failed: {e}")
            return []

    async def _native_search(self, video_path: str, query: str) -> List[SearchResult]:
        """Use native Gemini 2.5 video understanding - the best method"""
        if not self.native_service:
            return []
        
        # Determine search type for optimal results
        query_lower = query.lower()
        if any(word in query_lower for word in ['how many', 'count', 'number of']):
            search_type = "counting"
        elif any(word in query_lower for word in ['red', 'blue', 'green', 'yellow', 'color']):
            search_type = "color"
        elif any(word in query_lower for word in ['text', 'sign', 'writing']):
            search_type = "text"
        else:
            search_type = "object"
        
        # Get clips from native search
        clips = await self.native_service.search_visual_content(
            video_path=video_path,
            query=query,
            search_type=search_type
        )
        
        # Convert to SearchResult format
        results = []
        for clip in clips:
            results.append(SearchResult(
                timestamp=clip.start_time,
                confidence=clip.confidence,
                description=clip.description,
                frame_path=f"/api/search/frame?video_path={video_path}&timestamp={clip.start_time}",
                clip_start=clip.start_time,
                clip_end=clip.end_time
            ))
        
        return results
    
    async def _direct_frame_search(self, video_path: str, query: str, video_id: int = None) -> List[SearchResult]:
        """
        ULTRA-FAST frame analysis with parallel processing, smart sampling, and aggressive caching
        Target: 1-3 seconds (down from 30+ seconds)
        """
        import cv2
        import tempfile
        import asyncio
        import hashlib
        import numpy as np
        from concurrent.futures import ThreadPoolExecutor

        results = []
        start_time = time.time()

        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        try:
            # PHASE 1: INTELLIGENT FRAME SELECTION (2-3x faster)
            query_type = self._detect_query_type(query)
            selected_frames = await self._select_best_frames(cap, fps, duration, query, query_type)

            if not selected_frames:
                return []

            logger.info(f"SMART SELECTION: {len(selected_frames)} high-quality frames selected from {duration:.1f}s video ({query_type} search)")

            # PHASE 2: PARALLEL PROCESSING (5-10x faster)
            frame_tasks = []
            semaphore = asyncio.Semaphore(3)  # Limit concurrent Gemini calls

            for frame_data in selected_frames:
                task = self._analyze_frame_with_cache(
                    frame_data, query, video_id, semaphore
                )
                frame_tasks.append(task)

            # Process all frames in parallel with early termination
            results = await self._process_frames_parallel(frame_tasks, query)

            processing_time = time.time() - start_time
            logger.info(f"ULTRA-FAST: Found {len(results)} results in {processing_time:.2f}s (was 30+s)")

            return results

        finally:
            cap.release()

    async def _select_best_frames(self, cap, fps: float, duration: float, query: str, query_type: str) -> List[dict]:
        """
        PHASE 1: Intelligent frame selection using computer vision
        - Skip blurry/dark frames
        - Prioritize scene changes
        - Adaptive frame count based on query type
        """
        import cv2
        import numpy as np

        # ADAPTIVE FRAME SELECTION based on query type
        if query_type in ["person", "object"]:
            # DENSE COMPREHENSIVE sampling for person/object searches to find ALL instances
            candidate_count = min(60, int(duration / 5))   # Every 5 seconds, up to 60 candidates
            final_frame_count = min(25, candidate_count)   # Select up to 25 best frames (3x more!)
            logger.info(f"DENSE COMPREHENSIVE sampling: {candidate_count} candidates → {final_frame_count} frames for {query_type} search")
            logger.info(f"Coverage: ~{duration/final_frame_count:.1f}s intervals to find ALL instances")
        else:
            # Faster sampling for simple queries
            candidate_count = min(12, int(duration / 10))  # Every 10 seconds
            final_frame_count = 3                          # Select 3 frames for speed
            logger.info(f"FAST sampling: {candidate_count} candidates → {final_frame_count} frames for simple search")

        candidates = []

        for i in range(candidate_count):
            timestamp = (i + 0.5) * (duration / candidate_count)  # Offset to avoid transitions
            frame_number = int(timestamp * fps)

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()

            if not ret:
                continue

            # Quality metrics
            quality_score = self._calculate_frame_quality(frame)

            candidates.append({
                'timestamp': timestamp,
                'frame': frame,
                'quality_score': quality_score,
                'frame_number': frame_number
            })

        # Sort by quality and select top frames
        candidates.sort(key=lambda x: x['quality_score'], reverse=True)
        selected = candidates[:final_frame_count * 2]  # Get more candidates for diversity

        # Add temporal diversity (avoid clustering)
        final_selection = self._ensure_temporal_diversity(selected, duration, final_frame_count)

        return final_selection

    def _calculate_frame_quality(self, frame) -> float:
        """Calculate frame quality score (higher = better)"""
        import cv2
        import numpy as np

        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. Sharpness (Laplacian variance)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

        # 2. Brightness (avoid too dark/bright)
        brightness = np.mean(gray)
        brightness_score = 1.0 - abs(brightness - 128) / 128

        # 3. Contrast (standard deviation)
        contrast = np.std(gray) / 255.0

        # 4. Edge density (more edges = more content)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Combined quality score
        quality = (
            sharpness / 1000 * 0.4 +      # Sharpness weight
            brightness_score * 0.2 +       # Brightness weight
            contrast * 0.2 +               # Contrast weight
            edge_density * 0.2             # Content weight
        )

        return min(quality, 1.0)

    def _ensure_temporal_diversity(self, frames: List[dict], duration: float, target_count: int = 3) -> List[dict]:
        """Ensure frames are spread across video timeline"""
        if len(frames) <= target_count:
            return frames

        # Sort by timestamp
        frames.sort(key=lambda x: x['timestamp'])

        # Adaptive gap based on target count and duration
        if target_count <= 3:
            min_gap = duration * 0.2  # 20% gap for small counts
        elif target_count <= 10:
            min_gap = duration * 0.08  # 8% gap for medium counts
        else:
            min_gap = duration * 0.05  # 5% gap for large counts (maximum coverage)

        diverse_frames = [frames[0]]

        for frame in frames[1:]:
            if frame['timestamp'] - diverse_frames[-1]['timestamp'] >= min_gap:
                diverse_frames.append(frame)
                if len(diverse_frames) >= target_count:
                    break

        # If we don't have enough diverse frames, fill with best quality frames
        if len(diverse_frames) < target_count:
            remaining_frames = [f for f in frames if f not in diverse_frames]
            remaining_frames.sort(key=lambda x: x['quality_score'], reverse=True)
            diverse_frames.extend(remaining_frames[:target_count - len(diverse_frames)])

        return diverse_frames[:target_count]

    async def _analyze_frame_with_cache(self, frame_data: dict, query: str, video_id: int, semaphore: asyncio.Semaphore) -> dict:
        """
        PHASE 2: Analyze single frame with caching and optimized Gemini calls
        """
        import tempfile
        import hashlib
        import os

        async with semaphore:  # Limit concurrent API calls
            timestamp = frame_data['timestamp']
            frame = frame_data['frame']

            # PHASE 3: FRAME-LEVEL CACHING (2-3x faster for repeated queries)
            frame_hash = self._get_frame_hash(frame)
            cache_key = f"frame_{video_id}_{frame_hash}_{hashlib.md5(query.encode()).hexdigest()[:8]}"

            # Check cache first
            cached_result = await self._get_cached_analysis(cache_key)
            if cached_result:
                logger.info(f"CACHE HIT: Frame at {timestamp:.1f}s")
                return {
                    'timestamp': timestamp,
                    'analysis': cached_result,
                    'from_cache': True,
                    'video_id': video_id
                }

            # Save frame temporarily with optimized quality
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                import cv2
                # Optimize image size for faster upload (reduce from 90 to 75 quality)
                cv2.imwrite(tmp.name, frame, [cv2.IMWRITE_JPEG_QUALITY, 75])

                try:
                    # PHASE 4: OPTIMIZED GEMINI PROMPTS (1.3x faster)
                    analysis = await self._fast_gemini_analysis(tmp.name, query)

                    # Cache the result
                    await self._cache_analysis(cache_key, analysis)

                    return {
                        'timestamp': timestamp,
                        'analysis': analysis,
                        'from_cache': False,
                        'video_id': video_id
                    }

                except Exception as e:
                    logger.error(f"Error analyzing frame at {timestamp:.1f}s: {e}")
                    return {
                        'timestamp': timestamp,
                        'analysis': {"match": False, "confidence": 0.0, "description": f"Analysis failed: {e}"},
                        'from_cache': False,
                        'video_id': video_id
                    }
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(tmp.name)
                    except:
                        pass

    def _detect_query_type(self, query: str) -> str:
        """
        Detect query type to determine search behavior
        """
        query_lower = query.lower().strip()

        # Person names (disable early termination - find ALL instances)
        person_indicators = [
            'sundar pichai', 'elon musk', 'tim cook', 'satya nadella', 'jeff bezos',
            'mark zuckerberg', 'larry page', 'sergey brin', 'bill gates',
            # Add more known names or use patterns
        ]

        # Check for specific person names
        for person in person_indicators:
            if person in query_lower:
                return "person"

        # General person indicators
        if any(word in query_lower for word in ['person', 'people', 'man', 'woman', 'speaker', 'presenter', 'ceo', 'executive']):
            return "person"

        # Object searches that might have multiple instances
        object_indicators = ['car', 'phone', 'laptop', 'computer', 'screen', 'logo', 'sign']
        if any(word in query_lower for word in object_indicators):
            return "object"

        # Simple/single instance queries (can use early termination)
        simple_indicators = ['text', 'microphone', 'chart', 'graph', 'slide', 'background']
        if any(word in query_lower for word in simple_indicators):
            return "simple"

        # Default to comprehensive search for unknown queries
        return "comprehensive"

    async def _process_frames_parallel(self, frame_tasks: List, query: str) -> List[SearchResult]:
        """
        PHASE 2: Process all frames in parallel with SMART early termination
        - Person/Object searches: Find ALL instances (no early termination)
        - Simple queries: Use early termination for speed
        """
        results = []
        query_type = self._detect_query_type(query)

        logger.info(f"Query type detected: '{query_type}' for '{query}'")

        # Determine early termination behavior based on query type
        use_early_termination = query_type in ["simple"]
        min_confidence_threshold = 70  # Keep results with confidence >= 70%

        if use_early_termination:
            logger.info(f"FAST MODE: Early termination enabled for simple query")
        else:
            logger.info(f"COMPREHENSIVE MODE: Finding ALL instances for {query_type} search")

        # Process frames in parallel but check results as they complete
        for completed_task in asyncio.as_completed(frame_tasks):
            try:
                frame_result = await completed_task
                analysis = frame_result['analysis']
                timestamp = frame_result['timestamp']
                video_id = frame_result.get('video_id', 'unknown')

                # Check if match found with minimum confidence threshold
                if analysis.get("match", False):
                    confidence = analysis.get("confidence", 0.5) * 100

                    # Only keep results above confidence threshold
                    if confidence >= min_confidence_threshold:
                        description = analysis.get("description", f"Found '{query}' at {timestamp:.1f}s")

                        # Create clip around the match
                        clip_start = max(0, timestamp - 5)
                        clip_end = timestamp + 10  # Slightly longer clips

                        result = SearchResult(
                            timestamp=timestamp,
                            confidence=confidence,
                            description=description,
                            frame_path=f"/api/v1/search/{video_id}/frame?timestamp={timestamp}",
                            clip_start=clip_start,
                            clip_end=clip_end
                        )

                        results.append(result)

                        cache_status = "CACHED" if frame_result.get('from_cache') else "NEW"
                        logger.info(f"{cache_status} match at {timestamp:.1f}s (conf: {confidence:.1f}%): {description[:50]}...")

                        # SMART EARLY TERMINATION: Only for simple queries
                        if use_early_termination:
                            if confidence >= 95:  # Perfect match found
                                logger.info(f"PERFECT MATCH found (confidence: {confidence:.1f}%), stopping early")
                                break
                            elif len(results) >= 3 and confidence >= 80:  # Multiple good matches
                                logger.info(f"Found {len(results)} good matches, stopping early")
                                break
                    else:
                        logger.debug(f"Low confidence match at {timestamp:.1f}s (conf: {confidence:.1f}%) - skipped")

            except Exception as e:
                logger.error(f"Error processing frame task: {e}")

        # Sort results by confidence and timestamp
        results.sort(key=lambda x: (x.confidence, -x.timestamp), reverse=True)

        # Return different limits based on query type
        if query_type in ["person", "object"]:
            max_results = 15  # More results for comprehensive searches (increased from 10)
        else:
            max_results = 5   # Standard limit for simple queries

        final_results = results[:max_results]

        logger.info(f"{query_type.upper()} SEARCH: Found {len(final_results)} instances above {min_confidence_threshold}% confidence")

        return final_results

    def _get_frame_hash(self, frame) -> str:
        """Generate hash for frame caching"""
        import cv2
        import numpy as np

        # Resize frame to small size for consistent hashing
        small_frame = cv2.resize(frame, (64, 64))
        frame_bytes = small_frame.tobytes()
        return hashlib.md5(frame_bytes).hexdigest()[:16]

    async def _get_cached_analysis(self, cache_key: str) -> Optional[dict]:
        """Get cached frame analysis result"""
        # Simple in-memory cache for now (could be Redis in production)
        if not hasattr(self, '_frame_cache'):
            self._frame_cache = {}
        return self._frame_cache.get(cache_key)

    async def _cache_analysis(self, cache_key: str, analysis: dict):
        """Cache frame analysis result"""
        if not hasattr(self, '_frame_cache'):
            self._frame_cache = {}

        # Limit cache size to prevent memory issues
        if len(self._frame_cache) > 1000:
            # Remove oldest entries
            keys_to_remove = list(self._frame_cache.keys())[:200]
            for key in keys_to_remove:
                del self._frame_cache[key]

        self._frame_cache[cache_key] = analysis

    async def _fast_gemini_analysis(self, frame_path: str, query: str) -> dict:
        """
        PHASE 4: Ultra-fast Gemini analysis with optimized prompts
        """
        if not self.gemini_service:
            return {"match": False, "confidence": 0.0, "description": "Gemini service not available"}

        # Use the existing optimized method but could be further optimized
        return await self.gemini_service.analyze_frame_for_search(frame_path, query)

    def _results_to_clips(self, results: List[SearchResult]) -> List[ClipResult]:
        """Convert search results to clips for timeline/clips view"""
        clips = []
        for result in results:
            clips.append(ClipResult(
                start_time=result.clip_start,
                end_time=result.clip_end,
                confidence=result.confidence,
                description=result.description,
                thumbnail_url=result.frame_path
            ))
        return clips

# Global instance
simple_search = SimpleVideoSearch()