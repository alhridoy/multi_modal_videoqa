import React, { useState, useEffect } from 'react';
import { MapPin, Clock, Star, Filter, ChevronRight, Play, Eye, Bookmark } from 'lucide-react';

interface Moment {
  id: string;
  timestamp: number;
  duration: number;
  title: string;
  description: string;
  importance: 'high' | 'medium' | 'low';
  category: string;
  confidence: number;
  thumbnailUrl?: string;
  tags: string[];
}

interface MomentRetrievalProps {
  videoId: number;
  moments: Moment[];
  onTimeJump: (time: number) => void;
  onMomentSelect?: (moment: Moment) => void;
}

export const MomentRetrieval: React.FC<MomentRetrievalProps> = ({
  videoId,
  moments,
  onTimeJump,
  onMomentSelect
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedImportance, setSelectedImportance] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'timestamp' | 'importance' | 'confidence'>('timestamp');
  const [bookmarkedMoments, setBookmarkedMoments] = useState<Set<string>>(new Set());

  // Get unique categories
  const categories = ['all', ...Array.from(new Set(moments.map(m => m.category)))];

  // Filter and sort moments
  const filteredMoments = moments
    .filter(moment => {
      if (selectedCategory !== 'all' && moment.category !== selectedCategory) return false;
      if (selectedImportance !== 'all' && moment.importance !== selectedImportance) return false;
      return true;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'timestamp':
          return a.timestamp - b.timestamp;
        case 'importance':
          const importanceOrder = { high: 3, medium: 2, low: 1 };
          return importanceOrder[b.importance] - importanceOrder[a.importance];
        case 'confidence':
          return b.confidence - a.confidence;
        default:
          return 0;
      }
    });

  // Format time for display
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Format duration
  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  };

  // Get importance color
  const getImportanceColor = (importance: string): string => {
    switch (importance) {
      case 'high': return 'text-red-400 bg-red-400/20 border-red-400/30';
      case 'medium': return 'text-yellow-400 bg-yellow-400/20 border-yellow-400/30';
      case 'low': return 'text-green-400 bg-green-400/20 border-green-400/30';
      default: return 'text-gray-400 bg-gray-400/20 border-gray-400/30';
    }
  };

  // Toggle bookmark
  const toggleBookmark = (momentId: string) => {
    const newBookmarks = new Set(bookmarkedMoments);
    if (newBookmarks.has(momentId)) {
      newBookmarks.delete(momentId);
    } else {
      newBookmarks.add(momentId);
    }
    setBookmarkedMoments(newBookmarks);
  };

  return (
    <div className="bg-gray-900/80 rounded-lg border border-gray-700 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center">
            <MapPin className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="text-white font-medium">Moment Retrieval</h3>
            <p className="text-sm text-gray-400">Key moments and scenes</p>
          </div>
        </div>
        
        <div className="text-sm text-gray-400">
          {filteredMoments.length} of {moments.length} moments
        </div>
      </div>

      {/* Filters and Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-6 p-4 bg-gray-800/40 rounded-lg border border-gray-600">
        {/* Category Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-gray-800 text-white text-sm rounded px-2 py-1 border border-gray-600 focus:border-purple-500 focus:outline-none"
          >
            {categories.map(category => (
              <option key={category} value={category}>
                {category === 'all' ? 'All Categories' : category.charAt(0).toUpperCase() + category.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Importance Filter */}
        <select
          value={selectedImportance}
          onChange={(e) => setSelectedImportance(e.target.value)}
          className="bg-gray-800 text-white text-sm rounded px-2 py-1 border border-gray-600 focus:border-purple-500 focus:outline-none"
        >
          <option value="all">All Importance</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        {/* Sort By */}
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as any)}
          className="bg-gray-800 text-white text-sm rounded px-2 py-1 border border-gray-600 focus:border-purple-500 focus:outline-none"
        >
          <option value="timestamp">Sort by Time</option>
          <option value="importance">Sort by Importance</option>
          <option value="confidence">Sort by Confidence</option>
        </select>
      </div>

      {/* Moments List */}
      <div className="space-y-3 max-h-96 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-500/50 scrollbar-track-transparent">
        {filteredMoments.map((moment) => (
          <div
            key={moment.id}
            className="bg-gray-800/60 rounded-lg border border-gray-600 hover:border-purple-500/50 transition-all duration-200 cursor-pointer group"
            onClick={() => {
              onTimeJump(moment.timestamp);
              onMomentSelect?.(moment);
            }}
          >
            <div className="p-4">
              {/* Header Row */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  {/* Thumbnail */}
                  <div className="w-16 h-10 bg-gray-700 rounded overflow-hidden flex-shrink-0">
                    {moment.thumbnailUrl ? (
                      <img
                        src={moment.thumbnailUrl}
                        alt={moment.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Play className="w-4 h-4 text-gray-400" />
                      </div>
                    )}
                  </div>
                  
                  {/* Title and Time */}
                  <div className="flex-1">
                    <h4 className="text-white font-medium text-sm group-hover:text-purple-300 transition-colors">
                      {moment.title}
                    </h4>
                    <div className="flex items-center gap-2 mt-1">
                      <Clock className="w-3 h-3 text-gray-400" />
                      <span className="text-xs text-gray-400">
                        {formatTime(moment.timestamp)}
                      </span>
                      <span className="text-xs text-gray-500">•</span>
                      <span className="text-xs text-gray-400">
                        {formatDuration(moment.duration)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Controls */}
                <div className="flex items-center gap-2">
                  {/* Bookmark */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleBookmark(moment.id);
                    }}
                    className={`p-1 rounded transition-colors ${
                      bookmarkedMoments.has(moment.id)
                        ? 'text-yellow-400 hover:text-yellow-300'
                        : 'text-gray-400 hover:text-yellow-400'
                    }`}
                  >
                    <Bookmark className="w-4 h-4" />
                  </button>

                  {/* Importance Badge */}
                  <div className={`px-2 py-1 rounded text-xs font-medium border ${getImportanceColor(moment.importance)}`}>
                    {moment.importance}
                  </div>

                  {/* Confidence */}
                  <div className="text-xs text-gray-400">
                    {Math.round(moment.confidence * 100)}%
                  </div>

                  {/* Arrow */}
                  <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-purple-400 transition-colors" />
                </div>
              </div>

              {/* Description */}
              <p className="text-sm text-gray-300 mb-3 leading-relaxed">
                {moment.description}
              </p>

              {/* Tags and Category */}
              <div className="flex items-center justify-between">
                <div className="flex flex-wrap gap-1">
                  {moment.tags.slice(0, 3).map((tag, index) => (
                    <span
                      key={index}
                      className="inline-block px-2 py-1 bg-gray-700 rounded text-xs text-gray-300 border border-gray-600"
                    >
                      {tag}
                    </span>
                  ))}
                  {moment.tags.length > 3 && (
                    <span className="text-xs text-gray-400">
                      +{moment.tags.length - 3} more
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">{moment.category}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onTimeJump(moment.timestamp);
                    }}
                    className="opacity-0 group-hover:opacity-100 transition-opacity bg-purple-600 hover:bg-purple-500 text-white px-2 py-1 rounded text-xs font-medium flex items-center gap-1"
                  >
                    <Eye className="w-3 h-3" />
                    Jump
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="mt-4 pt-4 border-t border-gray-600">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <span className="text-gray-400">
              {moments.filter(m => m.importance === 'high').length} high importance
            </span>
            <span className="text-gray-400">
              {bookmarkedMoments.size} bookmarked
            </span>
          </div>
          <span className="text-gray-400">
            Total duration: {formatDuration(moments.reduce((sum, m) => sum + m.duration, 0))}
          </span>
        </div>
      </div>
    </div>
  );
};
