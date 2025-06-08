
import React, { useRef, useEffect, useState } from 'react';
import { Play, Volume2, Maximize, RotateCcw } from 'lucide-react';

// Declare YouTube API types
declare global {
  interface Window {
    YT: any;
    onYouTubeIframeAPIReady: () => void;
  }
}

interface VideoPlayerProps {
  videoUrl: string;
  title: string;
  currentTime?: number;
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({ videoUrl, title, currentTime = 0 }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const youtubePlayerRef = useRef<any>(null);
  const [isYouTubeAPIReady, setIsYouTubeAPIReady] = useState(false);
  const [youtubeVideoId, setYoutubeVideoId] = useState<string | null>(null);

  const isYouTubeUrl = (url: string) => {
    return url.includes('youtube.com') || url.includes('youtu.be');
  };

  const extractYouTubeVideoId = (url: string): string | null => {
    const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
  };

  // Load YouTube API
  useEffect(() => {
    if (isYouTubeUrl(videoUrl) && !window.YT) {
      const tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      const firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);

      window.onYouTubeIframeAPIReady = () => {
        setIsYouTubeAPIReady(true);
      };
    } else if (window.YT && window.YT.Player) {
      setIsYouTubeAPIReady(true);
    }
  }, [videoUrl]);

  // Initialize YouTube player
  useEffect(() => {
    if (isYouTubeUrl(videoUrl) && isYouTubeAPIReady) {
      const videoId = extractYouTubeVideoId(videoUrl);
      if (videoId) {
        setYoutubeVideoId(videoId);

        // Destroy existing player if it exists
        if (youtubePlayerRef.current && typeof youtubePlayerRef.current.destroy === 'function') {
          youtubePlayerRef.current.destroy();
        }

        // Small delay to ensure DOM element is ready
        setTimeout(() => {
          const playerElement = document.getElementById('youtube-player');
          if (playerElement && window.YT && window.YT.Player) {
            youtubePlayerRef.current = new window.YT.Player('youtube-player', {
              height: '100%',
              width: '100%',
              videoId: videoId,
              playerVars: {
                enablejsapi: 1,
                origin: window.location.origin,
                autoplay: 0,
                controls: 1,
              },
              events: {
                onReady: () => {
                  // YouTube player ready
                },
                onError: () => {
                  // YouTube player error
                },
              },
            });
          }
        }, 100);
      }
    }
  }, [videoUrl, isYouTubeAPIReady]);

  // Handle time jumping
  useEffect(() => {
    if (currentTime > 0) {
      if (isYouTubeUrl(videoUrl) && youtubePlayerRef.current) {
        // Check if YouTube player is ready and has seekTo method
        if (typeof youtubePlayerRef.current.seekTo === 'function') {
          try {
            youtubePlayerRef.current.seekTo(currentTime, true);
            // Also play the video after seeking
            if (typeof youtubePlayerRef.current.playVideo === 'function') {
              youtubePlayerRef.current.playVideo();
            }
          } catch (error) {
          }
        } else {
          // If player not ready, retry after a short delay
          setTimeout(() => {
            if (youtubePlayerRef.current && typeof youtubePlayerRef.current.seekTo === 'function') {
              youtubePlayerRef.current.seekTo(currentTime, true);
              if (typeof youtubePlayerRef.current.playVideo === 'function') {
                youtubePlayerRef.current.playVideo();
              }
            }
          }, 1000);
        }
      } else if (videoRef.current) {
        videoRef.current.currentTime = currentTime;
        videoRef.current.play().catch(() => {});
      }
    }
  }, [currentTime, videoUrl]);

  // Cleanup YouTube player on unmount
  useEffect(() => {
    return () => {
      if (youtubePlayerRef.current && typeof youtubePlayerRef.current.destroy === 'function') {
        youtubePlayerRef.current.destroy();
      }
    };
  }, []);

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-xl border border-white/20 overflow-hidden">
      {/* Video Header */}
      <div className="px-6 py-4 border-b border-white/10">
        <h2 className="text-xl font-semibold text-white truncate">{title}</h2>
      </div>

      {/* Video Container */}
      <div className="relative aspect-video bg-black">
        {isYouTubeUrl(videoUrl) ? (
          <div id="youtube-player" className="w-full h-full"></div>
        ) : (
          <video
            ref={videoRef}
            src={videoUrl}
            controls
            className="w-full h-full object-contain"
            preload="metadata"
          >
            Your browser does not support the video tag.
          </video>
        )}

        {/* Custom Overlay Controls (for future enhancement) */}
        <div className="absolute bottom-4 left-4 right-4 bg-black/50 rounded-lg p-3 opacity-0 hover:opacity-100 transition-opacity duration-300">
          <div className="flex items-center justify-between text-white">
            <div className="flex items-center gap-3">
              <button className="hover:text-purple-400 transition-colors">
                <Play className="w-5 h-5" />
              </button>
              <button className="hover:text-purple-400 transition-colors">
                <Volume2 className="w-5 h-5" />
              </button>
              <span className="text-sm">00:00 / 00:00</span>
            </div>
            
            <div className="flex items-center gap-2">
              <button className="hover:text-purple-400 transition-colors">
                <RotateCcw className="w-4 h-4" />
              </button>
              <button className="hover:text-purple-400 transition-colors">
                <Maximize className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
};

export default VideoPlayer;
