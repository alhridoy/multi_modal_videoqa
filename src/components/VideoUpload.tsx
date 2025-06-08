import React, { useState } from 'react';
import { Play, Video } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { apiService } from '@/services/api';

interface VideoUploadProps {
  onVideoUpload: (videoId: number, videoUrl: string, title: string) => void;
}

const VideoUpload: React.FC<VideoUploadProps> = ({ onVideoUpload }) => {
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const { toast } = useToast();

  const handleYouTubeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!youtubeUrl.trim()) return;

    // Validate YouTube URL
    if (!isValidYouTubeUrl(youtubeUrl)) {
      toast({
        title: "Invalid YouTube URL",
        description: "Please enter a valid YouTube video URL",
        variant: "destructive",
      });
      return;
    }

    setIsProcessing(true);

    try {
      const result = await apiService.processYouTubeVideo(youtubeUrl);

      onVideoUpload(result.video_id, youtubeUrl, result.title);
      toast({
        title: "YouTube video loaded!",
        description: `Processing complete. ${result.has_transcript ? 'Transcript available.' : 'No transcript found.'}`,
      });
    } catch (error) {
      toast({
        title: "Failed to process YouTube video",
        description: error instanceof Error ? error.message : "Please check the URL and try again",
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const isValidYouTubeUrl = (url: string): boolean => {
    const regex = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|embed\/|v\/)|youtu\.be\/)[\w-]{11}(&.*)?$/;
    return regex.test(url);
  };

  const extractYouTubeVideoId = (url: string): string | null => {
    const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
  };

  if (isProcessing) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-card border border-border rounded-2xl p-12 text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-foreground border-t-transparent mx-auto mb-6"></div>
          <h2 className="text-2xl font-bold text-foreground mb-2">Processing YouTube Video...</h2>
          <p className="text-muted-foreground">
            We're extracting the transcript and preparing it for AI analysis
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* YouTube URL Input */}
      <div className="bg-card border border-border rounded-2xl p-8">
        <div className="flex items-center gap-3 mb-6 justify-center">
          <Video className="w-10 h-10 text-red-600" />
          <h3 className="text-2xl font-bold text-foreground">
            Add YouTube Video
          </h3>
        </div>

        <p className="text-center text-muted-foreground mb-8">
          Enter a YouTube video URL to analyze and chat with the video content using AI
        </p>

        <form onSubmit={handleYouTubeSubmit} className="space-y-6">
          <div>
            <label htmlFor="youtube-url" className="block text-sm font-medium text-foreground mb-2">
              YouTube Video URL
            </label>
            <input
              id="youtube-url"
              type="url"
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
              className="w-full px-4 py-3 bg-input border border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={!youtubeUrl.trim() || isProcessing}
            className="w-full bg-red-600 hover:bg-red-700 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed text-white font-semibold py-4 px-6 rounded-lg transition-all duration-300 transform hover:scale-105 shadow-lg flex items-center justify-center gap-3"
          >
            <Play className="w-5 h-5" />
            Load & Analyze YouTube Video
          </button>
        </form>


        {/* Example URLs */}
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <p className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">Try with these example videos:</p>
          <div className="space-y-2">
            {[
              { url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ", title: "Classic Music Video" },
              { url: "https://www.youtube.com/watch?v=jNQXAC9IVRw", title: "Educational Content" },
            ].map((example, index) => (
              <button
                key={index}
                onClick={() => setYoutubeUrl(example.url)}
                className="block w-full text-left text-xs text-blue-700 dark:text-blue-300 hover:text-blue-900 dark:hover:text-blue-100 transition-colors p-2 rounded bg-white/50 dark:bg-black/20 hover:bg-white dark:hover:bg-black/40"
              >
                <span className="font-medium">{example.title}</span>
                <br />
                <span className="text-blue-600 dark:text-blue-400">{example.url}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoUpload;