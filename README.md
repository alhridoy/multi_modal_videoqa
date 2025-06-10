### APP Link ( Only local)
- https://videoanalysis-567h.vercel.app/

### Youtube videos
- https://youtu.be/VkCBWM2e9WY?si=TpzBh3aRLJI0APiq

  



### Backend
- **FastAPI** 
- **SQLAlchemy/Postgres** 
- **Google Gemini 2.5** 
- **ChromaDB**
- **FAISS**
- **FFmpeg** 
- **yt-dlp**
- **Redis**

### Frontend
- **React + TypeScript** 
- **Tailwind CSS** 
- **Vite** 
- **Lucide React**

### Deployment
- **Frontend: Vercel
-Backend: Render with postgres+ Redis
  

## Feature Guide
Challenge Requirements vs Your Implementation
1. Video Chat with RAG 
Challenge: Chat interface that answers questions about video content using RAG.

Implementation: The system uses vector search to find relevant transcript segments and generates contextual responses using Gemini AI.

2. Timestamped Citations 
Challenge: Responses should include clickable timestamps that jump to specific video sections.

 Implementation: GeminiService.generate_chat_response() includes citation extraction functionality that creates navigable links between AI responses and video timestamps.

3. Visual Content Search 
Challenge: Natural language queries to find specific visual content in frames (e.g., "red car").

Implementation:multiple approaches:

Direct Visual Search:  implements native video search using Gemini 2.5's video understanding capabilities
Multimodal Embeddings:  CLIP for direct image embeddings combined with text embeddings
Hybrid Search: combines keyword matching with vector similarit
##  Usage Guide

### 1. **Upload or Add YouTube Video**
- Paste a YouTube URL to analyze online content
- Wait for processing to complete (includes transcript extraction and frame analysis)

### 2. **Chat with Video**
- Use the chat interface to ask questions about the video
- Get responses with clickable timestamps
- Citations show relevant video moments

### 3. **Visual Search**
- Click "Visual Search" tab
- Enter natural language queries (e.g., "person with microphone", "red object")
- Browse results with confidence scores
- Jump to specific video moments

### 4. **Browse Sections**
- View auto-generated video sections
- Click timestamps to navigate to specific moments
- Explore key topics for each section
### Architecture Design

Component Architecture
![image](https://github.com/user-attachments/assets/b90645f2-d3af-4faf-ba68-22a7ace41015)

Video Processing and Analysis Pipeline
![image](https://github.com/user-attachments/assets/64c06d99-fc30-430f-ac4f-bd69ad216b00)


![image](https://github.com/user-attachments/assets/9c032516-a337-4847-80bf-c2c665292cb9)

### Key Challenge
 Video is 4-dimensional data (width × height × channels × time) with unique complexities:
Single frames vs. temporal sequences
Visual details transcripts miss
Actions spanning multiple frames
Multiple speakers with different emotions
Text appearing on screen

Most of the time treating video as a long continuous stream(like a long text document fails)  and multimodal embedding sometimes  fails; in testing, a red ball moving right vs. left produced nearly identical embedding scores (0.05 vs. 0.045). the model couldn't distinguish direction despite it being semantically crucial

 Where Gemini 2.5 Excels
1. Native Multimodal Integration
 Seamless audio-visual processing without separate pipelines
 Code generation from video (unique capability)
 Interactive applications from video analysis
2. Temporal Counting & Reasoning
 Accurate counting: 
Temporal order preservation:
 Complex reasoning

 Where Gemini 2.5 Falls Short
1. Fundamental Architecture Limitations
 Sequential processing: 1fps sampling misses rapid events
Frame limit: 256 frames (4+ minutes at 1fps) too restrictive
 No hierarchical structure: Can't preserve multi-scale temporal relationships
Early Fusion: all modalities together
2. Embedding Problems Persist
 No specialized indexing for different query types
 Unified approach may dilute specific capabilities


### Multimodal embedding fails, cause it tries to find needle in haystack


## References:
https://cohere.com/blog/multimodal-embeddings
https://www.youtube.com/watch?v=t1ik5ofs7Ok&ab_channel=KX
What are the common failure modes in multimodal search?

https://encord.com/blog/vision-language-models-guide/
The Multimodal Evolution of Vector Embeddings: https://www.youtube.com/watch?v=t1ik5ofs7Ok&ab_channel=KX
https://cohere.com/blog/multimodal-embeddings

https://blog.qburst.com/2021/12/multimodal-deep-learning-challenges-and-potential/




## Paper
VideoTree: Adaptive Tree-based Video Representation for LLM Reasoning

A New Hierarchical Key Frame Tree-Based Video Representation

https://arxiv.org/html/2408.11432v1
https://openaccess.thecvf.com/content_cvpr_2018/papers/Huang_What_Makes_a_CVPR_2018_paper.pdf

https://milvus.io/ai-quick-reference/what-are-the-common-failure-modes-in-multimodal-search
Content Based Video Retrieval Systems



AI-Powered Video Captioning Models for Hybrid Video Retrieval
Combining captioning with embeddings
RAG workflow integration
Visual content based video retrieval on natural language queries
Bidirectional retrieval approach
Joint embedding space learning
Enhancing Subsequent Video Retrieval via Vision-Language Models
https://ui.adsabs.harvard.edu/abs/2025arXiv250401407P/abstract


### SOTA results can be achieved 

Proposed Architecture:
Hybrid Triple Indexing
Input Video → Preprocessing → Tree Building → Indexing → Search Interface
     ↓              ↓             ↓           ↓            ↓
   Raw MP4    Frame/Audio    Root/Parent/   Triple      Query
              Extraction      Leaf Nodes    Indexing    Processing
```### ROOT (Overall video description)
├── PARENT (Key moments/highlights)
│   ├── LEAF (Granular segments)
│   └── LEAF (Visual embeddings)
└── PARENT (Another scene)
    ├── LEAF (Transcript segments)
    └── LEAF (More granular data)```
### TODO

. Three-Pillar Indexing System
A. Text Indexing
Purpose: Find when specific words/phrases were spoken
Implementation:
python# Sparse search (exact matching)
- Use Whisper v3 for transcription
- Store word-level timestamps
- Enable keyword search: "find where 'compute' was said"

# Dense embeddings (semantic search)
- Embed transcript segments
- Find conceptually related content
- "Find discussions about computation" (even if 'compute' wasn't said)


B. Visual Indexing
Purpose: Capture what happens visually without audio
Technical Approach:
python# Every 10-15 seconds:
1. Extract video segment
2. Generate multimodal embedding (maintains temporal features)
3. Index for visual-only queries


C. Highlight Indexing (VLM-based)
Purpose: Bridge the gap between embeddings and understanding
Process:
python# For each 10-60 second segment:
1. Feed to Vision Language Model (GPT-4V)
2. Generate detailed text description
3. Extract structured data (people, locations, events)
4. Create text embeddings of descriptions

### Hybrid Retrieval Pipeline

User Query
    ├── Text Search
    │   ├── Sparse (keywords)
    │   └── Dense (semantic)
    ├── Visual Search
    │   └── Multimodal embeddings
    └── Highlight Search
        └── VLM description embeddings
            ↓
    Aggregation & Scoring
            ↓
    Re-ranking (LLM with context)
            ↓
    Results with timestamps

Weight different indices based on query type
Use LLM as intelligent re-ranker
Leverage large context windows (1M+ tokens)


Transcribe → Identify people → Extract visual cues → Generate highlights with context


Transcribe ─┐
Visual     ─┼─→ Aggregate → Index
Highlights ─┘


Re-ranking:

GPT-4-turbo or similar
Need large context window support

Video File
    ├── Metadata DB
    │   ├── Title/Description (root)
    │   ├── Highlights (parents)
    │   └── Timestamps (leaves)
    ├── Embedding Store
    │   ├── Text embeddings
    │   └── Visual embeddings
    └── Transcript Store
        └── Word-level timestamps


Auto-tagging System

# During VLM processing:
structured_output = {
    "description": "...",
    "people": ["person1", "person2"],
    "locations": ["MIT campus"],
    "organizations": ["MIT"],
    "actions": ["presenting", "discussing"],
    "objects": ["laptop", "screen"]
}


Prompt Decomposition
python# "When did I talk to Ian about laptop stickers?"
decomposed = {
    "person_filter": "Ian",
    "topic_search": "laptop stickers",
    "temporal": "past conversations"
}
