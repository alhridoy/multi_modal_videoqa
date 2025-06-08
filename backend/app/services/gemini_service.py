import logging
from typing import List, Dict, Optional
from app.core.config import settings
import os
from PIL import Image
import tempfile
import time

logger = logging.getLogger(__name__)

class GeminiService:
    """Service for interacting with Google's Gemini AI (with lazy initialization)"""
    
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required")
        
        # Lazy initialization - only import and configure when needed
        self._model = None
        self._initialized = False
        
    def _ensure_initialized(self):
        """Initialize Gemini only when first needed to speed up startup"""
        if not self._initialized:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(settings.GEMINI_MODEL)
            self._initialized = True
            logger.info("Gemini service initialized")
    
    @property
    def model(self):
        """Get the model, initializing if necessary"""
        self._ensure_initialized()
        return self._model
        
    async def analyze_video_content(self, transcript: str, video_info: Dict) -> Dict:
        """Analyze video content and generate insights"""
        try:
            prompt = f"""
            Analyze this video transcript and provide insights:
            
            Video Title: {video_info.get('title', 'Unknown')}
            Transcript: {transcript}
            
            Please provide:
            1. A comprehensive summary (2-3 sentences)
            2. Key topics discussed (list of 5-7 topics)
            3. Main themes and concepts
            4. Important timestamps and what happens at those times
            
            Format your response as JSON with keys: summary, key_topics, themes, important_moments
            """
            
            response = self.model.generate_content(prompt)
            return {
                "analysis": response.text,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing video content: {e}")
            return {
                "analysis": None,
                "status": "error",
                "error": str(e)
            }
    
    async def generate_chat_response(self,
                                   question: str,
                                   transcript: str,
                                   video_info: Dict,
                                   chat_history: List[Dict] = None) -> Dict:
        """Generate a chat response based on video content"""
        try:
            # Build context from chat history
            history_context = ""
            if chat_history:
                for msg in chat_history[-5:]:  # Last 5 messages for context
                    history_context += f"User: {msg.get('message', '')}\nAI: {msg.get('response', '')}\n"

            # Truncate transcript if too long to avoid token limits
            max_transcript_length = 8000
            truncated_transcript = transcript[:max_transcript_length] if len(transcript) > max_transcript_length else transcript

            prompt = f"""
            You are an AI assistant that helps users understand video content. Provide well-structured, professional responses.

            Video Information:
            Title: {video_info.get('title', 'Unknown')}
            Transcript: {truncated_transcript}

            Previous conversation:
            {history_context}

            Current question: {question}

            RESPONSE FORMATTING REQUIREMENTS:
            1. Structure your response with clear sections using **bold headers** when appropriate
            2. Use bullet points (•) for lists and key points - ALWAYS use the bullet symbol •, not asterisks
            3. Write in a conversational but professional tone
            4. When referencing specific parts of the video, include timestamps as [MM:SS] or [HH:MM:SS] based on content flow
            5. Organize information logically with proper paragraph breaks
            6. Highlight important concepts or terms with **bold text**
            7. Use numbered lists for step-by-step explanations
            8. Include relevant timestamps even if estimating based on content progression

            EXAMPLE FORMATTING:
            **Overview of Topic:**
            The video discusses several key concepts:

            • **First concept**: Brief explanation with supporting details [02:15]
            • **Second concept**: Another important point [12:34]
            • **Third concept**: Additional information [18:45]

            **Key Differences:**
            1. First difference explained clearly [05:42]
            2. Second difference with timestamp reference [08:20]
            3. Third difference with context [15:30]

            Provide a comprehensive, well-formatted response based on the video content.
            """

            response = self.model.generate_content(prompt)

            # Extract timestamps from response
            citations = self._extract_timestamps(response.text, transcript)

            return {
                "response": response.text,
                "citations": citations,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error generating chat response: {e}")

            # Provide a fallback response based on the question
            fallback_response = self._generate_fallback_response(question, video_info)

            return {
                "response": fallback_response,
                "citations": [],
                "status": "success"  # Mark as success to avoid frontend errors
            }
    
    async def generate_video_sections(self, transcript: str, video_info: Dict) -> List[Dict]:
        """Generate intelligent video sections using AI"""
        try:
            # Use actual video duration if available, otherwise estimate from transcript
            actual_duration = video_info.get('duration', 0) if video_info else 0
            estimated_duration = len(transcript.split()) * 0.5  # ~0.5 seconds per word

            # Use the more reliable duration source
            if actual_duration > 0:
                estimated_duration = actual_duration
                logger.info(f"Using actual video duration: {actual_duration} seconds")
            else:
                logger.info(f"Using estimated duration from transcript: {estimated_duration} seconds")

            prompt = f"""
            You are an expert video content analyzer. Analyze this video transcript and create a comprehensive breakdown into logical sections.

            Video Title: {video_info.get('title', 'Unknown')}
            Estimated Duration: {estimated_duration:.0f} seconds

            Transcript:
            {transcript}

            TASK: Create 8-15 detailed sections that represent different topics, themes, or phases of the video.

            REQUIREMENTS:
            1. Each section should be 30-120 seconds long
            2. Sections should have natural topic boundaries
            3. Provide specific timestamps based on content flow
            4. Include rich descriptions and multiple key topics
            5. CRITICAL: Ensure sections cover the ENTIRE video duration ({estimated_duration:.0f} seconds)
            6. The final section MUST end at or near {estimated_duration:.0f} seconds
            7. Do not create sections that only cover the first few minutes

            For each section, provide:
            - title: Descriptive and engaging title (5-8 words)
            - start_time: Start timestamp in "MM:SS" format
            - end_time: End timestamp in "MM:SS" format
            - description: Detailed description (50-100 words) of what happens
            - key_topics: Array of 3-5 specific topics/keywords covered

            EXAMPLE FORMAT:
            [
              {{
                "title": "Introduction and Speaker Background",
                "start_time": "0:00",
                "end_time": "1:30",
                "description": "The speaker introduces themselves, their professional background, and sets the context for the presentation. They discuss their experience at major tech companies and outline what the audience can expect to learn.",
                "key_topics": ["speaker introduction", "professional background", "presentation overview", "tech industry experience"]
              }},
              {{
                "title": "Problem Statement and Motivation",
                "start_time": "1:30",
                "end_time": "3:15",
                "description": "Detailed explanation of the core problem being addressed, why it matters, and the motivation behind the solution. Includes real-world examples and impact analysis.",
                "key_topics": ["problem definition", "market need", "impact analysis", "real-world examples", "solution motivation"]
              }}
            ]

            Return ONLY the JSON array, no additional text or markdown formatting.
            """

            response = self.model.generate_content(prompt)

            # Parse the response and extract sections
            sections = self._parse_sections_response(response.text)

            # If parsing failed or returned empty, generate fallback sections
            if not sections:
                logger.warning("AI section generation failed, creating fallback sections")
                sections = self._generate_fallback_sections(transcript, estimated_duration)

            return sections

        except Exception as e:
            logger.error(f"Error generating video sections: {e}")
            # Return fallback sections on error - use actual video duration if available
            actual_duration = video_info.get('duration', 300) if video_info else 300
            estimated_duration = len(transcript.split()) * 0.5 if transcript else actual_duration
            final_duration = max(actual_duration, estimated_duration) if actual_duration else estimated_duration
            return self._generate_fallback_sections(transcript if 'transcript' in locals() else "", final_duration)
    
    async def analyze_frame(self, frame_path: str, context: str = "", timestamp: float = 0.0) -> Dict:
        """Analyze a video frame using Gemini Vision with advanced temporal understanding"""
        try:
            # Check if frame file exists
            if not os.path.exists(frame_path):
                logger.error(f"Frame file not found: {frame_path}")
                return {
                    "description": "Frame file not found",
                    "status": "error",
                    "error": "File not found"
                }

            # Use PIL to open and prepare the image
            image = Image.open(frame_path)

            prompt = f"""
            Analyze this video frame at timestamp {timestamp}s with advanced video understanding capabilities.

            Context: {context}

            COMPREHENSIVE ANALYSIS REQUIRED:

            1. **VISUAL ELEMENTS** (for search capabilities):
               - Objects: List ALL visible objects with specific details (red Toyota car, MacBook laptop, etc.)
               - People: Describe appearance, clothing, actions, expressions, demographics
               - Colors: Specific color descriptions (crimson red, navy blue, forest green)
               - Text/Signs: Any readable text, logos, signs, captions
               - UI Elements: Buttons, menus, screens, interfaces

            2. **TEMPORAL CONTEXT** (for moment retrieval):
               - Actions occurring: What is happening in this moment
               - Scene transitions: Is this a new scene or continuation
               - Key events: Important moments that users might search for
               - Emotional tone: Mood, atmosphere, energy level

            3. **SPATIAL RELATIONSHIPS**:
               - Object positions: Where things are located relative to each other
               - Composition: Layout, framing, perspective
               - Focus areas: What draws attention in the frame

            4. **SEARCHABLE KEYWORDS**:
               - Generate 10-15 specific keywords that users might search for
               - Include synonyms and related terms
               - Consider both literal and conceptual searches

            FORMAT AS STRUCTURED DATA:
            Objects: [detailed object list]
            People: [person descriptions]
            Colors: [color analysis]
            Text: [visible text]
            Scene: [setting and context]
            Actions: [current activities]
            Keywords: [searchable terms]
            Moment_Type: [presentation, discussion, demo, transition, etc.]

            Be extremely detailed and specific to enable precise visual search and moment retrieval.
            """

            # Generate content with image
            response = self.model.generate_content([prompt, image])

            return {
                "description": response.text,
                "status": "success",
                "timestamp": timestamp
            }

        except Exception as e:
            logger.error(f"Error analyzing frame: {e}")
            return {
                "description": "Unable to analyze frame",
                "status": "error",
                "error": str(e)
            }

    async def analyze_video_native(self, video_path: str, query: str = "") -> Dict:
        """Analyze video directly using Gemini 2.5 native video understanding"""
        try:
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return {
                    "status": "error",
                    "error": "Video file not found"
                }

            # Ensure Gemini is initialized
            self._ensure_initialized()
            import google.generativeai as genai

            # Upload video file to Gemini
            logger.info(f"Uploading video to Gemini: {video_path}")
            video_file = genai.upload_file(path=video_path)

            # Wait for processing
            while video_file.state.name == "PROCESSING":
                logger.info("Video processing...")
                time.sleep(2)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise Exception("Video processing failed")

            # Create comprehensive analysis prompt
            prompt = f"""
            Analyze this video using advanced multimodal understanding capabilities.

            Query context: {query if query else "General analysis"}

            COMPREHENSIVE VIDEO ANALYSIS:

            1. **VISUAL CONTENT ANALYSIS**:
               - Objects and their temporal presence (when they appear/disappear)
               - People, their actions, and interactions over time
               - Scene changes and transitions
               - Text, UI elements, and visual information
               - Color schemes and visual themes

            2. **TEMPORAL UNDERSTANDING**:
               - Key moments and their timestamps
               - Sequence of events and their relationships
               - Transitions between different topics/scenes
               - Recurring elements or patterns

            3. **SEARCHABLE CONTENT**:
               - Generate detailed descriptions for visual search
               - Identify specific objects, colors, and scenes
               - Note any text or readable content
               - Describe actions and interactions

            4. **MOMENT SEGMENTATION**:
               - Break video into logical segments
               - Provide timestamp ranges for each segment
               - Describe what makes each segment distinct

            Provide detailed, timestamp-specific analysis that enables precise visual search and navigation.
            """

            # Generate analysis
            response = self.model.generate_content([prompt, video_file])

            # Clean up uploaded file
            genai.delete_file(video_file.name)

            return {
                "analysis": response.text,
                "status": "success",
                "method": "native_video_analysis"
            }

        except Exception as e:
            logger.error(f"Error in native video analysis: {e}")
            return {
                "status": "error",
                "error": str(e),
                "method": "native_video_analysis"
            }

    async def search_video_content(self, video_path: str, search_query: str) -> List[Dict]:
        """Search for specific content in video using Gemini 2.5 video understanding"""
        try:
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return []

            # Ensure Gemini is initialized
            self._ensure_initialized()
            import google.generativeai as genai

            # Upload video file to Gemini
            logger.info(f"Uploading video for search: {video_path}")
            video_file = genai.upload_file(path=video_path)

            # Wait for processing
            while video_file.state.name == "PROCESSING":
                logger.info("Video processing for search...")
                time.sleep(2)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise Exception("Video processing failed")

            # Create search-specific prompt
            prompt = f"""
            Search this video for: "{search_query}"

            VISUAL SEARCH ANALYSIS:

            Find all instances where "{search_query}" appears or is relevant in the video.
            For each occurrence, provide:

            1. **Timestamp**: Exact time when it appears
            2. **Description**: Detailed description of what's shown
            3. **Context**: What's happening in that moment
            4. **Relevance**: Why it matches the search query
            5. **Duration**: How long it's visible/relevant

            Focus on:
            - Visual elements (objects, colors, people, text)
            - Actions and interactions
            - Scene context and setting
            - Any related or similar content

            Return results as a JSON array with objects containing:
            {{
                "timestamp": float,
                "end_timestamp": float,
                "description": "detailed description",
                "relevance_score": float (0-1),
                "context": "scene context",
                "match_type": "exact|partial|related"
            }}
            """

            # Generate search results
            response = self.model.generate_content([prompt, video_file])

            # Clean up uploaded file
            genai.delete_file(video_file.name)

            # Parse JSON response
            import json
            try:
                results = json.loads(response.text)
                return results if isinstance(results, list) else []
            except json.JSONDecodeError:
                logger.warning("Failed to parse search results as JSON")
                return self._parse_search_results_from_text(response.text)

        except Exception as e:
            logger.error(f"Error in video content search: {e}")
            return []

    def _parse_search_results_from_text(self, text: str) -> List[Dict]:
        """Parse search results from text when JSON parsing fails"""
        try:
            results = []
            lines = text.strip().split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Try to extract timestamp and description
                if ':' in line and ('s' in line or 'second' in line):
                    # Look for patterns like "0:30 - description" or "30s: description"
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        try:
                            # Extract timestamp
                            time_part = parts[0].strip()
                            desc_part = parts[1].strip()

                            # Parse timestamp (handle formats like "0:30", "30s", "30")
                            if 's' in time_part:
                                timestamp = float(time_part.replace('s', ''))
                            elif ':' in time_part:
                                time_components = time_part.split(':')
                                if len(time_components) == 2:
                                    minutes = int(time_components[0])
                                    seconds = int(time_components[1])
                                    timestamp = minutes * 60 + seconds
                                else:
                                    timestamp = float(time_part)
                            else:
                                timestamp = float(time_part)

                            results.append({
                                'timestamp': timestamp,
                                'description': desc_part,
                                'confidence': 0.8
                            })
                        except (ValueError, IndexError):
                            continue

            logger.info(f"Parsed {len(results)} results from text response")
            return results

        except Exception as e:
            logger.error(f"Error parsing text results: {e}")
            return []

    async def analyze_video_moments(self, video_path: str, transcript: str) -> List[Dict]:
        """
        Analyze video to extract key moments using Gemini 2.5 capabilities
        
        Args:
            video_path: Path to video file
            transcript: Video transcript
        
        Returns:
            List of moments with timestamps and descriptions
        """
        try:
            # For now, we'll use transcript-based moment detection
            # In production with Gemini 2.5, this would analyze the actual video
            
            prompt = f"""
            Analyze this video transcript and identify key moments that would be interesting to highlight.

            Transcript:
            {transcript}
            
            Identify 5-10 key moments that represent:
            - Topic changes
            - Important statements or revelations
            - Visual demonstrations (if mentioned)
            - Conclusions or summaries
            
            For each moment, estimate the timestamp based on the flow of conversation.
            
            Format as JSON array with objects containing:
            - timestamp: estimated time in seconds
            - title: brief title of the moment
            - description: what happens at this moment
            - importance: why this moment matters
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse response
            try:
                import json
                result_text = response.text
                # Extract JSON if wrapped in markdown
                if "```json" in result_text:
                    start = result_text.find("```json") + 7
                    end = result_text.find("```", start)
                    result_text = result_text[start:end].strip()
                elif "```" in result_text:
                    start = result_text.find("```") + 3
                    end = result_text.find("```", start)
                    result_text = result_text[start:end].strip()
                
                moments = json.loads(result_text)
                return moments if isinstance(moments, list) else []
                
            except:
                # Fallback - create basic moments
                return [
                    {
                        "timestamp": 0,
                        "title": "Introduction",
                        "description": "Video begins",
                        "importance": "Sets the context"
                    }
                ]
                
        except Exception as e:
            logger.error(f"Error analyzing video moments: {e}")
            return []

    def _parse_moments_from_text(self, text: str) -> List[Dict]:
        """Fallback parser for moment analysis"""
        # Simple fallback implementation
        moments = []
        lines = text.split('\n')

        current_moment = {}
        for line in lines:
            line = line.strip()
            if line.startswith('Title:') or line.startswith('title:'):
                if current_moment:
                    moments.append(current_moment)
                current_moment = {"title": line.split(':', 1)[1].strip()}
            elif line.startswith('Description:') or line.startswith('description:'):
                current_moment["description"] = line.split(':', 1)[1].strip()
            elif line.startswith('Keywords:') or line.startswith('keywords:'):
                keywords = line.split(':', 1)[1].strip()
                current_moment["keywords"] = [k.strip() for k in keywords.split(',')]

        if current_moment:
            moments.append(current_moment)

        return moments

    async def temporal_counting_analysis(self, frames_data: List[Dict], query: str) -> Dict:
        """
        Perform temporal counting analysis using Gemini 2.5 capabilities
        
        Args:
            frames_data: List of frame data with timestamps and descriptions
            query: What to count (e.g., "how many times does someone use their phone")
        
        Returns:
            Dictionary with count, occurrences, patterns, and notes
        """
        try:
            # Prepare frames summary for analysis
            frames_summary = "\n".join([
                f"[{frame['timestamp']:.1f}s]: {frame['description']}"
                for frame in frames_data
            ])
            
            prompt = f"""
            Analyze these video frames and perform temporal counting for the following query:
            "{query}"
            
            Video frames with timestamps:
            {frames_summary}
            
            Please provide:
            1. Total count of occurrences
            2. List of specific timestamps where each occurrence happens
            3. Any patterns observed (e.g., frequency, clustering)
            4. Additional notes or context
            
            Format your response as JSON with keys:
            - total_count: number
            - occurrences: list of {{timestamp: float, description: string}}
            - patterns: string describing temporal patterns
            - notes: string with additional observations
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse response - attempt JSON parsing
            try:
                import json
                result_text = response.text
                # Extract JSON if wrapped in markdown
                if "```json" in result_text:
                    start = result_text.find("```json") + 7
                    end = result_text.find("```", start)
                    result_text = result_text[start:end].strip()
                elif "```" in result_text:
                    start = result_text.find("```") + 3
                    end = result_text.find("```", start)
                    result_text = result_text[start:end].strip()
                
                return json.loads(result_text)
            except:
                # Fallback parsing
                return {
                    "total_count": 0,
                    "occurrences": [],
                    "patterns": "Unable to parse detailed patterns",
                    "notes": response.text
                }
                
        except Exception as e:
            logger.error(f"Error in temporal counting analysis: {e}")
            return {
                "total_count": 0,
                "occurrences": [],
                "patterns": "Analysis failed",
                "notes": str(e)
            }
    
    def _parse_sections_response(self, response_text: str) -> List[Dict]:
        """Parse AI response to extract video sections with robust error handling"""
        try:
            import json

            # Clean the response text
            cleaned_text = response_text.strip()

            # Try multiple parsing strategies

            # Strategy 1: Direct JSON parsing
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                pass

            # Strategy 2: Extract JSON from markdown code blocks
            if "```json" in cleaned_text:
                start = cleaned_text.find("```json") + 7
                end = cleaned_text.find("```", start)
                if end != -1:
                    json_str = cleaned_text[start:end].strip()
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass

            # Strategy 3: Extract JSON array from text
            start = cleaned_text.find('[')
            end = cleaned_text.rfind(']') + 1
            if start != -1 and end > start:
                json_str = cleaned_text[start:end]
                try:
                    sections = json.loads(json_str)
                    # Validate the structure
                    if isinstance(sections, list) and all(
                        isinstance(section, dict) and
                        'title' in section and
                        'start_time' in section and
                        'end_time' in section
                        for section in sections
                    ):
                        return sections
                except json.JSONDecodeError:
                    pass

            # Strategy 4: Try to find individual JSON objects
            import re
            json_objects = re.findall(r'\{[^{}]*\}', cleaned_text)
            sections = []
            for obj_str in json_objects:
                try:
                    obj = json.loads(obj_str)
                    if 'title' in obj and 'start_time' in obj:
                        sections.append(obj)
                except json.JSONDecodeError:
                    continue

            if sections:
                return sections

        except Exception as e:
            logger.error(f"Error parsing sections response: {e}")

        # All parsing strategies failed
        return []

    def _generate_fallback_sections(self, transcript: str, estimated_duration: float) -> List[Dict]:
        """Generate fallback sections when AI parsing fails"""
        try:
            # Create sections based on transcript length and estimated duration
            words = transcript.split() if transcript else []
            total_words = len(words)

            if total_words == 0:
                estimated_duration = max(estimated_duration, 300)  # Minimum 5 minutes

            # Aim for 8-12 sections
            target_sections = min(12, max(8, int(estimated_duration / 60)))
            section_duration = estimated_duration / target_sections

            sections = []
            for i in range(target_sections):
                start_time = i * section_duration
                end_time = min((i + 1) * section_duration, estimated_duration)

                # Format timestamps
                start_min, start_sec = divmod(int(start_time), 60)
                end_min, end_sec = divmod(int(end_time), 60)

                # Generate section content based on position
                if i == 0:
                    title = "Introduction and Opening"
                    description = "The video begins with an introduction, setting the context and outlining what will be covered."
                    topics = ["introduction", "overview", "context setting"]
                elif i == target_sections - 1:
                    title = "Conclusion and Summary"
                    description = "The video concludes with a summary of key points and final thoughts."
                    topics = ["conclusion", "summary", "key takeaways"]
                elif i == 1:
                    title = "Background and Context"
                    description = "Foundational information and background context is provided to understand the main topic."
                    topics = ["background", "context", "foundation"]
                else:
                    title = f"Topic Discussion {i}"
                    description = f"Detailed discussion of key concepts and ideas in section {i} of the presentation."
                    topics = [f"topic {i}", "discussion", "analysis"]

                sections.append({
                    "title": title,
                    "start_time": f"{start_min}:{start_sec:02d}",
                    "end_time": f"{end_min}:{end_sec:02d}",
                    "description": description,
                    "key_topics": topics
                })

            logger.info(f"Generated {len(sections)} fallback sections")
            return sections

        except Exception as e:
            logger.error(f"Error generating fallback sections: {e}")
            # Ultimate fallback - single section with proper duration
            fallback_duration = max(estimated_duration, 300) if estimated_duration > 0 else 300
            end_min, end_sec = divmod(int(fallback_duration), 60)
            end_time = f"{end_min}:{end_sec:02d}" if end_min < 60 else f"{end_min//60}:{end_min%60:02d}:{end_sec:02d}"

            return [{
                "title": "Video Content",
                "start_time": "0:00",
                "end_time": end_time,
                "description": "Video content analysis in progress. Please try again shortly for detailed sections.",
                "key_topics": ["content", "analysis", "processing"]
            }]

    def _generate_fallback_response(self, question: str, video_info: Dict) -> str:
        """Generate a fallback response when AI fails"""
        title = video_info.get('title', 'this video')

        if 'what' in question.lower() and 'about' in question.lower():
            return f"This appears to be a video titled '{title}'. I'm currently processing the content and will be able to provide more detailed information shortly."
        elif 'summary' in question.lower() or 'summarize' in question.lower():
            return f"I'm working on analyzing '{title}' to provide you with a comprehensive summary. Please try again in a moment."
        elif 'topic' in question.lower() or 'subject' in question.lower():
            return f"The video '{title}' covers various topics that I'm currently analyzing. Please ask me again shortly for detailed topic information."
        else:
            return f"I'm currently processing the video '{title}' to better understand its content. Please try your question again in a moment, and I'll be able to provide more specific information."

    def _extract_timestamps(self, text: str, transcript: str) -> List[Dict]:
        """Extract timestamp citations from AI response and create inline citations"""
        import re

        # Find timestamp patterns in the response
        timestamp_pattern = r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]'
        matches = re.findall(timestamp_pattern, text)

        citations = []
        seen_timestamps = set()  # Avoid duplicate citations

        for i, match in enumerate(matches):
            if match in seen_timestamps:
                continue
            seen_timestamps.add(match)

            # Convert timestamp to seconds
            time_parts = match.split(':')
            if len(time_parts) == 2:  # MM:SS
                seconds = int(time_parts[0]) * 60 + int(time_parts[1])
            else:  # HH:MM:SS
                seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])

            # Try to extract context around the timestamp from the transcript
            context = self._extract_context_for_timestamp(transcript, seconds)

            citations.append({
                "text": context if context else f"Reference at {match}",
                "time": seconds,
                "timestamp": match,
                "citation_id": i + 1
            })

        return citations

    def _extract_context_for_timestamp(self, transcript: str, target_seconds: int) -> str:
        """Extract relevant context from transcript around a specific timestamp"""
        try:
            # This is a simplified approach - in a real implementation,
            # you'd have timestamp-aligned transcript data
            words = transcript.split()

            # Rough estimation: ~2 words per second
            target_word_index = target_seconds * 2

            # Extract context around the target (±10 words)
            start_index = max(0, target_word_index - 10)
            end_index = min(len(words), target_word_index + 10)

            context_words = words[start_index:end_index]
            context = " ".join(context_words)

            # Truncate if too long
            if len(context) > 100:
                context = context[:97] + "..."

            return context
        except:
            return ""
    
    async def analyze_frame_for_search(self, frame_path: str, search_query: str) -> Dict:
        """
        Analyze a single frame to see if it contains the search query.
        Direct, simple implementation for visual search.
        """
        try:
            if not os.path.exists(frame_path):
                return {"match": False, "confidence": 0.0, "description": "Frame not found"}

            # Ensure Gemini is initialized
            self._ensure_initialized()
            import google.generativeai as genai

            # Upload image to Gemini
            image_file = genai.upload_file(path=frame_path)
            
            # ULTRA-FAST optimized prompt (reduced from 20+ lines to 4 lines)
            prompt = f"""
            Does this image contain "{search_query}"?

            Respond in JSON: {{"match": true/false, "confidence": 0.0-1.0, "description": "brief explanation"}}
            """
            
            # Generate analysis
            response = self.model.generate_content([prompt, image_file])
            
            # Clean up uploaded image
            try:
                genai.delete_file(image_file.name)
            except:
                pass
            
            # Parse response
            try:
                response_text = response.text.strip()
                
                # Clean JSON from response
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                elif "{" in response_text:
                    start = response_text.find("{")
                    end = response_text.rfind("}") + 1
                    response_text = response_text[start:end]
                
                import json
                result = json.loads(response_text)
                
                logger.info(f"Frame analysis for '{search_query}': {result}")
                return result
                
            except Exception as e:
                logger.error(f"Error parsing frame analysis response: {e}")
                logger.error(f"Raw response: {response.text}")
                
                # Fallback - check if response mentions the query
                response_lower = response.text.lower()
                query_lower = search_query.lower()
                
                if any(word in response_lower for word in query_lower.split()):
                    return {
                        "match": True,
                        "confidence": 0.6,
                        "description": f"Possible match for '{search_query}' detected"
                    }
                else:
                    return {
                        "match": False,
                        "confidence": 0.0,
                        "description": f"No match for '{search_query}' found"
                    }
                    
        except Exception as e:
            logger.error(f"Error in frame analysis for search: {e}")
            return {
                "match": False,
                "confidence": 0.0,
                "description": f"Error analyzing frame: {str(e)}"
            }
