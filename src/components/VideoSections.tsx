
import React, { useState, useEffect } from 'react';
import { Clock, Play, Hash } from 'lucide-react';
import { apiService, VideoSection } from '@/services/api';
import { useToast } from '@/hooks/use-toast';

interface VideoSectionsProps {
  videoId: number;
  videoUrl: string;
  videoDuration?: number; // Add video duration prop
  onTimeJump: (time: number) => void;
}

const VideoSections: React.FC<VideoSectionsProps> = ({ videoId, videoUrl, videoDuration, onTimeJump }) => {
  const [sections, setSections] = useState<VideoSection[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  // Calculate total video duration for timeline calculations
  const totalDuration = videoDuration || 420; // Default to 7 minutes if not provided

  useEffect(() => {
    const fetchSections = async () => {
      try {
        setLoading(true);
        const response = await apiService.getVideoSections(videoId);
        setSections(response.sections || []);
      } catch (error) {
        toast({
          title: "Error loading sections",
          description: error instanceof Error ? error.message : "Failed to load video sections",
          variant: "destructive",
        });
        // Fallback to mock data
        setSections([
          {
            id: 1,
            title: 'Introduction & Background',
            start_time: 0,
            end_time: 45,
            description: 'Speaker introduces themselves and their background working at Microsoft and Google',
            key_topics: ['Speaker background', 'Big Tech experience', 'Exaflop consulting']
          },
          {
            id: 2,
            title: 'Project Overview',
            start_time: 45,
            end_time: 120,
            description: 'Overview of the video analysis project and its main objectives',
            key_topics: ['Video data', 'Query and search', 'AI analysis']
          },
          {
            id: 3,
            title: 'Chat with Videos Feature',
            start_time: 120,
            end_time: 210,
            description: 'Detailed explanation of the RAG-based video chat functionality',
            key_topics: ['RAG implementation', 'Video upload', 'Chat interface']
          }
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchSections();
  }, [videoId, toast]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const parseTimeToSeconds = (timeStr: string): number => {
    const parts = timeStr.split(':');
    if (parts.length === 2) {
      return parseInt(parts[0]) * 60 + parseInt(parts[1]);
    }
    return 0;
  };

  const getDuration = (startTime: number, endTime: number): string => {
    const duration = endTime - startTime;
    return `${Math.floor(duration / 60)}:${(duration % 60).toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="h-full flex flex-col bg-black">
        <div className="text-center mb-4 flex-shrink-0">
          <h3 className="text-lg font-semibold text-white mb-2">Video Sections</h3>
          <p className="text-sm text-gray-300">Loading sections...</p>
        </div>
        <div className="flex-1 animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-gray-900/80 rounded-lg p-4 h-24 border border-gray-700"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-black">
      {/* Header */}
      <div className="text-center mb-4 flex-shrink-0">
        <h3 className="text-lg font-semibold text-white mb-2">Video Sections</h3>
        <p className="text-sm text-gray-300">
          AI-generated breakdown with clickable timestamps
        </p>
      </div>

      {/* Sections List - Scrollable */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-gray-500/50 scrollbar-track-transparent">
        {sections.map((section, index) => (
          <div
            key={section.id}
            className="bg-gray-900/80 rounded-lg border border-gray-700 p-4 hover:bg-gray-800/80 transition-all duration-300 cursor-pointer group"
            onClick={() => onTimeJump(parseTimeToSeconds(section.start_time))}
          >
            {/* Section Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center text-black font-semibold text-sm">
                  {index + 1}
                </div>
                <div>
                  <h4 className="font-medium text-white group-hover:text-gray-300 transition-colors">
                    {section.title}
                  </h4>
                  <div className="flex items-center gap-4 text-xs text-gray-400 mt-1">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {section.start_time} - {section.end_time}
                    </span>
                    <span>Duration: {getDuration(parseTimeToSeconds(section.start_time), parseTimeToSeconds(section.end_time))}</span>
                  </div>
                </div>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onTimeJump(parseTimeToSeconds(section.start_time));
                }}
                className="opacity-0 group-hover:opacity-100 transition-opacity bg-white hover:bg-gray-200 text-black p-2 rounded-full transform hover:scale-110 transition-transform"
              >
                <Play className="w-4 h-4" />
              </button>
            </div>

            {/* Section Description */}
            <p className="text-sm text-gray-300 mb-3 leading-relaxed">
              {section.description}
            </p>

            {/* Key Topics */}
            <div className="flex flex-wrap gap-2">
              {section.key_topics.map((topic, topicIndex) => (
                <span
                  key={topicIndex}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-gray-800 rounded text-xs text-gray-300 border border-gray-600"
                >
                  <Hash className="w-3 h-3" />
                  {topic}
                </span>
              ))}
            </div>

            {/* Progress Bar */}
            <div className="mt-3 h-1 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-white rounded-full"
                style={{
                  width: `${((parseTimeToSeconds(section.end_time) - parseTimeToSeconds(section.start_time)) / totalDuration) * 100}%`
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Timeline Overview */}
      <div className="mt-4 p-4 bg-gray-900/80 rounded-lg border border-gray-700 flex-shrink-0">
        <h4 className="text-sm font-medium text-white mb-3">Timeline Overview</h4>
        <div className="relative h-2 bg-gray-700 rounded-full">
          {sections.map((section) => (
            <div
              key={section.id}
              className="absolute top-0 h-full bg-white rounded-full cursor-pointer hover:opacity-80 transition-opacity"
              style={{
                left: `${(parseTimeToSeconds(section.start_time) / totalDuration) * 100}%`,
                width: `${((parseTimeToSeconds(section.end_time) - parseTimeToSeconds(section.start_time)) / totalDuration) * 100}%`,
              }}
              onClick={() => onTimeJump(parseTimeToSeconds(section.start_time))}
              title={`${section.title} (${section.start_time})`}
            />
          ))}
        </div>
        <div className="flex justify-between text-xs text-gray-400 mt-2">
          <span>0:00</span>
          <span>{Math.floor(totalDuration / 60)}:{(totalDuration % 60).toString().padStart(2, '0')}</span>
        </div>
      </div>
    </div>
  );
};

export default VideoSections;
