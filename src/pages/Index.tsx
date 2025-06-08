
import React, { useState, useEffect } from 'react';
import VideoUpload from '../components/VideoUpload';
import VideoPlayer from '../components/VideoPlayer';
import ChatInterface from '../components/ChatInterface';
import VideoSections from '../components/VideoSections';
import VisualSearch from '../components/VisualSearch';
import HealthCheck from '../components/HealthCheck';
import { Video, MessageSquare, Search, Clock } from 'lucide-react';
import { apiService } from '../services/api';

const Index = () => {
  const [uploadedVideo, setUploadedVideo] = useState<string | null>(null);
  const [videoTitle, setVideoTitle] = useState<string>('');
  const [videoId, setVideoId] = useState<number | null>(null);
  const [videoDuration, setVideoDuration] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'chat' | 'sections' | 'search'>('chat');
  const [currentTime, setCurrentTime] = useState(0);

  const handleVideoUpload = (id: number, videoUrl: string, title: string) => {
    setVideoId(id);
    setUploadedVideo(videoUrl);
    setVideoTitle(title);
  };

  const handleTimeJump = (time: number) => {
    setCurrentTime(time);
  };

  // Fetch video duration when videoId changes
  useEffect(() => {
    const fetchVideoDuration = async () => {
      if (videoId) {
        try {
          const videoInfo = await apiService.getVideo(videoId);
          setVideoDuration(videoInfo.duration || null);
        } catch (error) {
        }
      }
    };

    fetchVideoDuration();
  }, [videoId]);

  const tabs = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'sections', label: 'Sections', icon: Clock },
    { id: 'search', label: 'Visual Search', icon: Search },
  ];

  return (
    <div className="min-h-screen bg-background">
      <HealthCheck />
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Video className="w-10 h-10 text-foreground" />
            <h1 className="text-4xl font-bold text-foreground">VideoChat AI</h1>
          </div>
          <p className="text-xl text-muted-foreground">
            Upload, analyze, and chat with your videos using AI
          </p>
        </div>

        {!uploadedVideo ? (
          <VideoUpload onVideoUpload={handleVideoUpload} />
        ) : (
          <div className="space-y-6">
            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Video Player Section */}
              <div className="lg:col-span-2">
                <VideoPlayer
                  videoUrl={uploadedVideo}
                  title={videoTitle}
                  currentTime={currentTime}
                />
              </div>

              {/* Right Sidebar - Only Chat and Sections */}
              <div className="lg:col-span-1">
                <div className="bg-black border border-gray-700 rounded-xl p-6 h-full">
                  {/* Tab Navigation - Only Chat and Sections */}
                  <div className="flex rounded-lg bg-gray-900 p-1 mb-6">
                    {tabs.filter(tab => tab.id !== 'search').map((tab) => {
                      const Icon = tab.icon;
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id as any)}
                          className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-md transition-all duration-200 ${
                            activeTab === tab.id
                              ? 'bg-white text-black shadow-lg'
                              : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                          }`}
                        >
                          <Icon className="w-4 h-4" />
                          <span className="text-sm font-medium">{tab.label}</span>
                        </button>
                      );
                    })}
                  </div>

                  {/* Tab Content */}
                  <div className="h-[600px] overflow-hidden">
                    {activeTab === 'chat' && videoId && (
                      <ChatInterface
                        videoId={videoId}
                        videoUrl={uploadedVideo}
                        onTimeJump={handleTimeJump}
                      />
                    )}
                    {activeTab === 'sections' && videoId && (
                      <VideoSections
                        videoId={videoId}
                        videoUrl={uploadedVideo}
                        videoDuration={videoDuration || undefined}
                        onTimeJump={handleTimeJump}
                      />
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Visual Search Section - Full Width Below Video */}
            {videoId && (
              <div className="w-full">
                <div className="bg-black border border-gray-700 rounded-xl p-6">
                  {/* Visual Search Header */}
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
                      <Search className="w-5 h-5 text-primary-foreground" />
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold text-white">Visual Search</h2>
                      <p className="text-gray-400 text-sm">Find anything in your video using AI-powered visual analysis</p>
                    </div>
                  </div>

                  {/* Visual Search Component */}
                  <VisualSearch
                    videoId={videoId}
                    videoUrl={uploadedVideo}
                    onTimeJump={handleTimeJump}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Index;
