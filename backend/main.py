from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
import logging
from contextlib import asynccontextmanager

from app.api.routes import video, chat, search
from app.core.config import settings
from app.core.database import engine, Base
from app.services.video_processor import VideoProcessor
from app.services.gemini_service import GeminiService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting VideoChat AI Backend...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Create thumbnail directory if it doesn't exist
    os.makedirs("thumbnails", exist_ok=True)
    
    # Create frames directory if it doesn't exist
    os.makedirs("uploads/frames", exist_ok=True)
    
    # Initialize services
    video_processor = VideoProcessor()
    gemini_service = GeminiService()

    # Store services in app state
    app.state.video_processor = video_processor
    app.state.gemini_service = gemini_service
    
    logger.info("Backend startup complete!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down VideoChat AI Backend...")

# Create FastAPI app
app = FastAPI(
    title="VideoChat AI Backend",
    description="Multimodal video analysis system with chat and visual search capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure with specific origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(video.router, prefix="/api/v1/video", tags=["video"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])

# Mount static files for thumbnails and frames
app.mount("/api/thumbnails", StaticFiles(directory="thumbnails"), name="thumbnails")
app.mount("/api/frames", StaticFiles(directory="uploads/frames"), name="frames")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "VideoChat AI Backend is running!",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "database": "connected",
            "gemini": "available",
            "video_processor": "ready"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
