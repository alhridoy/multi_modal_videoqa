# Multi-Modal Video Q&A System

An advanced video analysis application that combines AI-powered chat capabilities with visual search functionality. Upload videos, ask questions about their content, and get intelligent responses powered by Google's Gemini AI.

## 🚀 Features

- **Video Upload & Processing**: Support for multiple video formats with automatic frame extraction
- **AI-Powered Chat**: Ask questions about video content using natural language
- **Visual Search**: Search through video frames using semantic similarity
- **Multimodal Understanding**: Combines video, audio, and text analysis
- **Real-time Processing**: Fast video analysis with optimized frame extraction
- **Modern UI**: Clean, responsive interface built with React and Tailwind CSS

## 🛠 Technology Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **SQLAlchemy** - Database ORM with SQLite
- **Google Gemini 2.5** - Advanced multimodal AI for video understanding
- **ChromaDB** - Vector database for semantic search
- **FFmpeg** - Video processing and frame extraction
- **yt-dlp** - YouTube video downloading

### Frontend
- **React + TypeScript** - Modern web interface
- **Tailwind CSS** - Utility-first styling
- **Vite** - Fast development and build tool
- **Lucide React** - Beautiful icons

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- FFmpeg installed
- Google Gemini API key

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/alhridoy/multi_modal_videoqa.git
cd multi_modal_videoqa
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Create required directories
mkdir -p thumbnails uploads/frames

# Start the backend server
python3 main.py
```

### 3. Frontend Setup
```bash
# In a new terminal, from the root directory
npm install
npm run dev
```

### 4. Access the Application
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the `backend` directory with the following variables:

```env
# Google Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///./videochat.db

# Application Settings
DEBUG=True
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"]
MAX_VIDEO_SIZE_MB=500
FRAME_EXTRACTION_INTERVAL=5

# Model Configuration
GEMINI_MODEL=gemini-2.5-flash
```

### Getting a Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key to your `.env` file

## 📱 Usage

1. **Upload a Video**: Click the upload button and select a video file
2. **Wait for Processing**: The system will extract frames and analyze the video
3. **Ask Questions**: Use the chat interface to ask questions about the video content
4. **Visual Search**: Search for specific scenes or objects within the video

## 🏗 Project Structure

```
multi_modal_videoqa/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   └── services/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── lib/
├── public/
├── package.json
└── README.md
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Gemini AI for multimodal understanding
- FastAPI for the robust backend framework
- React and Vite for the modern frontend experience

## 📞 Support

If you have any questions or need help, please open an issue on GitHub.

---

**Built with ❤️ for intelligent video analysis**
