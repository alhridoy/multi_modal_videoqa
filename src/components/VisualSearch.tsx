import React, { useState, useEffect, useCallback } from 'react';
import { Search, Eye, Clock, Zap, Film, ChevronDown, ChevronUp, Users, Target, Play, ChevronLeft, ChevronRight, Grid3X3, BarChart3 } from 'lucide-react';
import { SearchResult, ClipResult, SearchSuggestionsResponse, apiService } from '@/services/api';
import { useToast } from '@/hooks/use-toast';

interface VisualSearchProps {
  videoId: number;
  videoUrl: string;
  onTimeJump: (time: number) => void;
}

const VisualSearch: React.FC<VisualSearchProps> = ({ videoId, onTimeJump }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchClips, setSearchClips] = useState<ClipResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [viewMode, setViewMode] = useState<'clips' | 'frames' | 'timeline'>('clips');
  const [directAnswer, setDirectAnswer] = useState<string>('');
  const [queryType, setQueryType] = useState<string>('');
  const [expandedResults, setExpandedResults] = useState<Set<number>>(new Set());
  const [currentClipIndex, setCurrentClipIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [suggestionsError, setSuggestionsError] = useState<string>('');

  const { toast } = useToast();

  // Load dynamic suggestions when video changes
  useEffect(() => {
    const loadSuggestions = async () => {
      if (!videoId) return;
      
      setSuggestionsLoading(true);
      setSuggestionsError('');
      
      try {
        const suggestionsResponse = await apiService.getSearchSuggestions(videoId);
        setSuggestions(suggestionsResponse.suggestions || []);
        
        // Show toast about suggestion generation method
        if (suggestionsResponse.generation_method === 'hybrid') {
          toast({
            title: "Smart suggestions generated",
            description: `Found ${suggestionsResponse.total_suggestions} contextual search terms from video content and transcript.`,
          });
        } else if (suggestionsResponse.generation_method === 'ai_analysis') {
          toast({
            title: "AI-powered suggestions",
            description: `Generated ${suggestionsResponse.total_suggestions} visual search terms using AI analysis.`,
          });
        }
        
      } catch (error) {
        console.error('Failed to load suggestions:', error);
        setSuggestionsError('Failed to generate suggestions');
        
        // Fallback to basic suggestions
        setSuggestions(['person', 'speaker', 'microphone', 'background', 'text on screen', 'camera']);
        
      } finally {
        setSuggestionsLoading(false);
      }
    };

    loadSuggestions();
  }, [videoId, toast]);

  // Add keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!hasSearched || searchClips.length === 0) return;
      
      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          navigateToClip(Math.max(0, currentClipIndex - 1));
          break;
        case 'ArrowRight':
          e.preventDefault();
          navigateToClip(Math.min(searchClips.length - 1, currentClipIndex + 1));
          break;
        case ' ':
          e.preventDefault();
          if (searchClips[currentClipIndex]) {
            onTimeJump(searchClips[currentClipIndex].start_time);
            setIsPlaying(!isPlaying);
          }
          break;
        case 'Enter':
          e.preventDefault();
          if (searchClips[currentClipIndex]) {
            onTimeJump(searchClips[currentClipIndex].start_time);
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentClipIndex, searchClips, hasSearched, isPlaying, onTimeJump]);

  const navigateToClip = useCallback((index: number) => {
    if (index >= 0 && index < searchClips.length) {
      setCurrentClipIndex(index);
      onTimeJump(searchClips[index].start_time);
    }
  }, [searchClips, onTimeJump]);

  const formatDuration = (seconds: number): string => {
    return `${Math.round(seconds * 10) / 10}s`;
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      // Clear results if search is empty
      setSearchResults([]);
      setSearchClips([]);
      setDirectAnswer('');
      setQueryType('');
      setHasSearched(false);
      setCurrentClipIndex(0);
      return;
    }

    setIsSearching(true);
    setHasSearched(true);
    setExpandedResults(new Set()); // Reset expanded results

    try {
      
      // Use real API call to search video content with the native search enabled
      const response = await apiService.visualSearch(videoId, searchQuery.trim(), 10);
      

      setSearchResults(response.results || []);
      setSearchClips(response.clips || []);
      setDirectAnswer(response.direct_answer || '');
      setQueryType(response.query_type || '');
      setCurrentClipIndex(0); // Reset to first clip

      const hasResults = (response.results || []).length > 0 || (response.clips || []).length > 0;

      if (!hasResults) {
        // Provide more specific guidance based on processing method
        let processingMessage = "No visual content matching your query was found.";
        
        if (response.processing_method === "direct_frame_analysis") {
          processingMessage = `Direct frame analysis completed but found no matches for "${searchQuery}". Try more general terms or check if the content exists in your video.`;
        } else if (response.processing_method === "native_video_search") {
          processingMessage = "Native video search found no matches. The video may need more processing time or the content might not be visually detectable.";
        } else if (response.processing_method === "semantic_search") {
          processingMessage = "Semantic search found no matches. Try uploading the video again or use different keywords.";
        } else {
          processingMessage = "No matches found. Try keywords like 'person', 'microphone', 'red car', 'text', or 'background'.";
        }
        
        toast({
          title: "No results found", 
          description: processingMessage,
        });
      } else {
        const totalResults = (response.clips || []).length + (response.results || []).length;
        const method = response.processing_method ? ` using ${response.processing_method}` : '';
        
        toast({
          title: "Search completed",
          description: `Found ${totalResults} ${totalResults === 1 ? 'result' : 'results'} for "${searchQuery}"${method}`,
        });
      }
    } catch (error) {
      
      // More detailed error handling
      let errorMessage = "Failed to search video content";
      if (error instanceof Error) {
        if (error.message.includes('404')) {
          errorMessage = "Video not found. Please make sure the video is uploaded and processed.";
        } else if (error.message.includes('500')) {
          errorMessage = "Server error during search. The video might need to be processed first.";
        } else {
          errorMessage = error.message;
        }
      }
      
      toast({
        title: "Search failed",
        description: errorMessage,
        variant: "destructive",
      });
      
      // Clear results on error
      setSearchResults([]);
      setSearchClips([]);
      setDirectAnswer('');
      setQueryType('');
    } finally {
      setIsSearching(false);
    }
  };

  // Add real-time search as user types (but only on manual submit, not auto-search)
  useEffect(() => {
    if (!searchQuery.trim()) {
      // Clear results if query is empty
      setSearchResults([]);
      setSearchClips([]);
      setDirectAnswer('');
      setQueryType('');
      setHasSearched(false);
      setCurrentClipIndex(0);
    }
  }, [searchQuery]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 90) return 'text-green-400';
    if (confidence >= 75) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const toggleExpandResult = (index: number) => {
    const newExpanded = new Set(expandedResults);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedResults(newExpanded);
  };

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search for anything... (e.g., 'person', 'red car', 'microphone')"
            className="w-full px-4 py-4 pl-12 pr-12 bg-input border border-border rounded-xl text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all text-lg shadow-sm"
            disabled={isSearching}
          />
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          {searchQuery && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                setSearchResults([]);
                setSearchClips([]);
                setDirectAnswer('');
                setQueryType('');
                setHasSearched(false);
                setCurrentClipIndex(0);
              }}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted-foreground hover:text-foreground transition-colors"
              title="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        {/* Dynamic Search Suggestions */}
        {!hasSearched && (
          <div className="space-y-3">
            {suggestionsLoading ? (
              <div className="flex items-center justify-center gap-2 text-muted-foreground">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-muted-foreground border-t-transparent"></div>
                <span className="text-sm">Analyzing video for smart suggestions...</span>
              </div>
            ) : suggestionsError ? (
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">Using default suggestions</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {suggestions.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => setSearchQuery(suggestion)}
                      className="px-4 py-2 text-sm bg-muted hover:bg-primary hover:text-primary-foreground text-muted-foreground rounded-full transition-all border border-border hover:border-primary shadow-sm hover:shadow-md"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : suggestions.length > 0 ? (
              <div className="space-y-2">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Smart suggestions based on your video content:</p>
                </div>
                <div className="flex flex-wrap gap-2 justify-center">
                  {suggestions.slice(0, 12).map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => setSearchQuery(suggestion)}
                      className="px-4 py-2 text-sm bg-gradient-to-r from-primary/10 to-primary/5 hover:from-primary hover:to-primary/90 hover:text-primary-foreground text-foreground rounded-full transition-all border border-primary/20 hover:border-primary shadow-sm hover:shadow-md font-medium"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
                {suggestions.length > 12 && (
                  <div className="text-center">
                    <button
                      onClick={() => {
                        // You could implement a "show more" feature here
                        const remainingSuggestions = suggestions.slice(12);
                        setSuggestions([...suggestions.slice(0, 12), ...remainingSuggestions]);
                      }}
                      className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >
                      +{suggestions.length - 12} more suggestions available
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2 justify-center">
                {['person', 'speaker', 'microphone', 'background', 'text on screen', 'camera'].map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => setSearchQuery(suggestion)}
                    className="px-4 py-2 text-sm bg-muted hover:bg-primary hover:text-primary-foreground text-muted-foreground rounded-full transition-all border border-border hover:border-primary shadow-sm hover:shadow-md"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <button
          type="submit"
          disabled={!searchQuery.trim() || isSearching}
          className="w-full bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed text-primary-foreground font-semibold py-4 px-6 rounded-xl transition-all duration-300 transform hover:scale-[1.02] shadow-lg hover:shadow-xl flex items-center justify-center gap-3 text-lg"
        >
          {isSearching ? (
            <>
              <div className="animate-spin rounded-full h-6 w-6 border-2 border-primary-foreground border-t-transparent"></div>
              Analyzing Video...
            </>
          ) : (
            <>
              <Eye className="w-6 h-6" />
              Search with AI
            </>
          )}
        </button>
      </form>

      {/* Search Results */}
      {hasSearched && (
        <div className="space-y-4">
          {isSearching ? (
            <div className="text-center py-8">
              <div className="animate-pulse space-y-4">
                <div className="w-16 h-16 bg-muted rounded-full mx-auto flex items-center justify-center">
                  <Zap className="w-8 h-8 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground">
                  AI is analyzing video frames for "{searchQuery}"
                </p>
              </div>
            </div>
          ) : searchResults.length > 0 || searchClips.length > 0 ? (
            <>
              {/* Direct Answer Section */}
              {directAnswer && (
                <div className="mb-4 p-4 bg-muted/50 rounded-lg border border-border">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center flex-shrink-0">
                      {queryType === 'counting' ? (
                        <Users className="w-4 h-4 text-primary-foreground" />
                      ) : (
                        <Target className="w-4 h-4 text-primary-foreground" />
                      )}
                    </div>
                    <div className="flex-1">
                      <h4 className="text-foreground font-medium mb-1">Direct Answer</h4>
                      <p className="text-muted-foreground text-sm leading-relaxed">{directAnswer}</p>
                      {queryType && (
                        <span className="inline-block mt-2 px-2 py-1 bg-muted rounded text-xs text-muted-foreground border border-border">
                          {queryType.replace('_', ' ')}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Results Header with View Toggle */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h4 className="text-foreground font-medium">
                    Found {searchClips.length > 0 ? `${searchClips.length} clips` : `${searchResults.length} matches`} for "{searchQuery}"
                  </h4>
                  <p className="text-sm text-muted-foreground mt-1">
                    {searchClips.length > 0 
                      ? `${searchClips.length} video segments with ${searchResults.length} total frames detected`
                      : searchResults.length > 1 
                        ? 'Multiple instances detected throughout the video. Click any result to jump to that moment' 
                        : 'Click result to jump to that moment in the video'
                    }
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {searchClips.length > 0 && (
                    <button
                      onClick={() => setViewMode('clips')}
                      className={`px-3 py-1.5 rounded text-sm font-medium transition-all ${
                        viewMode === 'clips'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                      }`}
                    >
                      <Film className="w-4 h-4 inline mr-1" />
                      Clips ({searchClips.length})
                    </button>
                  )}
                  {searchClips.length > 0 && (
                    <button
                      onClick={() => setViewMode('timeline')}
                      className={`px-3 py-1.5 rounded text-sm font-medium transition-all ${
                        viewMode === 'timeline'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                      }`}
                    >
                      <BarChart3 className="w-4 h-4 inline mr-1" />
                      Timeline
                    </button>
                  )}
                  <button
                    onClick={() => setViewMode('frames')}
                    className={`px-3 py-1.5 rounded text-sm font-medium transition-all ${
                      viewMode === 'frames'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                    }`}
                  >
                    <Grid3X3 className="w-4 h-4 inline mr-1" />
                    Frames ({searchResults.length})
                  </button>
                </div>
              </div>

              {/* Clips View */}
              {viewMode === 'clips' && searchClips.length > 0 && (
                <div className="space-y-4">
                  {/* Clip Navigation */}
                  <div className="flex items-center justify-between bg-muted/30 rounded-lg p-3">
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-muted-foreground">
                        Clip {currentClipIndex + 1} of {searchClips.length}
                      </span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => navigateToClip(currentClipIndex - 1)}
                          disabled={currentClipIndex === 0}
                          className="p-1 rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                          title="Previous clip (←)"
                        >
                          <ChevronLeft className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => navigateToClip(currentClipIndex + 1)}
                          disabled={currentClipIndex === searchClips.length - 1}
                          className="p-1 rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                          title="Next clip (→)"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Use ← → keys to navigate • Space to play/pause • Enter to jump
                    </div>
                  </div>

                  {/* Clips Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {searchClips.map((clip, index) => (
                      <div
                        key={index}
                        className={`group bg-card rounded-lg border transition-all duration-300 cursor-pointer ${
                          index === currentClipIndex
                            ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                            : 'border-border hover:border-primary/50 hover:bg-muted/30'
                        }`}
                        onClick={() => {
                          setCurrentClipIndex(index);
                          onTimeJump(clip.start_time);
                        }}
                      >
                        {/* Clip Thumbnail */}
                        <div className="relative aspect-video bg-muted/50 rounded-t-lg overflow-hidden">
                          {/* Thumbnail Image */}
                          {clip.thumbnail_url ? (
                            <img 
                              src={`http://localhost:8001${clip.thumbnail_url}`}
                              alt={`Clip ${index + 1} thumbnail`}
                              className="w-full h-full object-cover transition-transform group-hover:scale-105"
                              onError={(e) => {
                                const target = e.currentTarget;
                                target.style.display = 'none';
                                // Show fallback thumbnail icon
                                const fallback = target.nextElementSibling as HTMLElement;
                                if (fallback) fallback.style.display = 'flex';
                              }}
                            />
                          ) : null}
                          
                          {/* Fallback thumbnail when no real thumbnail is available */}
                          <div
                            className="absolute inset-0 flex items-center justify-center bg-muted/80"
                            style={{ display: clip.thumbnail_url ? 'none' : 'flex' }}
                          >
                            <Film className="w-12 h-12 text-muted-foreground" />
                          </div>
                          
                          {/* Play button overlay */}
                          <div className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity">
                            <div className="bg-primary/90 rounded-full p-3 shadow-lg">
                              <Play className="w-6 h-6 text-primary-foreground" />
                            </div>
                          </div>
                          
                          {/* Clip Info Overlay */}
                          <div className="absolute top-2 left-2 flex gap-1">
                            <span className="bg-black/80 text-white text-xs px-2 py-1 rounded font-medium">
                              #{index + 1}
                            </span>
                            <span className="bg-primary/90 text-primary-foreground text-xs px-2 py-1 rounded font-medium">
                              {formatDuration(clip.end_time - clip.start_time)}
                            </span>
                          </div>
                          
                          {/* Confidence Badge */}
                          <div className="absolute top-2 right-2">
                            <span className={`text-xs px-2 py-1 rounded font-medium ${
                              clip.confidence >= 90 
                                ? 'bg-green-500/90 text-white' 
                                : clip.confidence >= 75 
                                  ? 'bg-yellow-500/90 text-white'
                                  : 'bg-orange-500/90 text-white'
                            }`}>
                              {clip.confidence}%
                            </span>
                          </div>
                        </div>

                        {/* Clip Details */}
                        <div className="p-4">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <Clock className="w-3 h-3" />
                              <span>{formatTime(clip.start_time)} - {formatTime(clip.end_time)}</span>
                            </div>
                            <span className="text-xs text-muted-foreground">
                              {clip.frame_count} frames
                            </span>
                          </div>
                          
                          <p className="text-sm text-foreground leading-relaxed overflow-hidden" style={{
                            display: '-webkit-box',
                            WebkitBoxOrient: 'vertical',
                            WebkitLineClamp: 2
                          }}>
                            {clip.description}
                          </p>
                          
                          {/* Clip Actions */}
                          <div className="flex gap-2 mt-3">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onTimeJump(clip.start_time);
                              }}
                              className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground px-3 py-2 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1"
                            >
                              <Play className="w-3 h-3" />
                              Jump to clip
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Timeline View */}
              {viewMode === 'timeline' && searchClips.length > 0 && (
                <div className="space-y-4">
                  <div className="bg-muted/30 rounded-lg p-4">
                    <h5 className="text-sm font-medium text-foreground mb-3">
                      Clip Timeline ({searchClips.length} clips found)
                    </h5>
                    <div className="relative">
                      {/* Timeline bar */}
                      <div className="h-8 bg-muted rounded-lg relative overflow-hidden border border-border">
                        {searchClips.map((clip, index) => {
                          const totalDuration = Math.max(...searchClips.map(c => c.end_time));
                          const startPercent = (clip.start_time / totalDuration) * 100;
                          const widthPercent = ((clip.end_time - clip.start_time) / totalDuration) * 100;
                          
                          return (
                            <div
                              key={index}
                              className={`absolute h-full rounded transition-all cursor-pointer flex items-center justify-center ${
                                index === currentClipIndex
                                  ? 'bg-primary shadow-lg z-10'
                                  : 'bg-primary/60 hover:bg-primary/80 hover:z-10'
                              }`}
                              style={{
                                left: `${startPercent}%`,
                                width: `${Math.max(2, widthPercent)}%`,  // Ensure minimum width for visibility
                                minWidth: '20px'  // Minimum width to ensure clickability
                              }}
                              onClick={() => {
                                setCurrentClipIndex(index);
                                onTimeJump(clip.start_time);
                              }}
                              title={`Clip ${index + 1}: ${formatTime(clip.start_time)} - ${formatTime(clip.end_time)}`}
                            >
                              <span className="text-xs font-medium text-primary-foreground">{index + 1}</span>
                            </div>
                          );
                        })}
                      </div>
                      
                      {/* Timeline markers */}
                      <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                        <span>0:00</span>
                        <span className="text-center">{formatTime(Math.max(...searchClips.map(c => c.end_time)) / 2)}</span>
                        <span>{formatTime(Math.max(...searchClips.map(c => c.end_time)))}</span>
                      </div>
                      
                      {/* Clip indicators below timeline */}
                      <div className="mt-3 flex flex-wrap gap-2">
                        {searchClips.map((clip, index) => (
                          <button
                            key={index}
                            onClick={() => {
                              setCurrentClipIndex(index);
                              onTimeJump(clip.start_time);
                            }}
                            className={`px-2 py-1 rounded text-xs font-medium transition-all ${
                              index === currentClipIndex
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                            }`}
                          >
                            Clip {index + 1} ({formatTime(clip.start_time)})
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                  
                  {/* Current clip details */}
                  {searchClips[currentClipIndex] && (
                    <div className="bg-card rounded-lg border p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h6 className="font-medium text-foreground mb-1">
                            Clip {currentClipIndex + 1}: {formatTime(searchClips[currentClipIndex].start_time)} - {formatTime(searchClips[currentClipIndex].end_time)}
                          </h6>
                          <p className="text-sm text-muted-foreground">
                            {searchClips[currentClipIndex].description}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">
                            {formatDuration(searchClips[currentClipIndex].end_time - searchClips[currentClipIndex].start_time)}
                          </span>
                          <span className={`text-xs font-medium px-2 py-1 rounded ${getConfidenceColor(searchClips[currentClipIndex].confidence)} bg-muted`}>
                            {searchClips[currentClipIndex].confidence}%
                          </span>
                        </div>
                      </div>
                      
                      <div className="flex gap-2">
                        <button
                          onClick={() => onTimeJump(searchClips[currentClipIndex].start_time)}
                          className="bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded text-sm font-medium transition-colors flex items-center gap-2"
                        >
                          <Play className="w-4 h-4" />
                          Play this clip
                        </button>
                        <button
                          onClick={() => navigateToClip(currentClipIndex - 1)}
                          disabled={currentClipIndex === 0}
                          className="bg-muted hover:bg-accent text-muted-foreground hover:text-accent-foreground px-3 py-2 rounded text-sm font-medium transition-colors flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <ChevronLeft className="w-4 h-4" />
                          Previous
                        </button>
                        <button
                          onClick={() => navigateToClip(currentClipIndex + 1)}
                          disabled={currentClipIndex === searchClips.length - 1}
                          className="bg-muted hover:bg-accent text-muted-foreground hover:text-accent-foreground px-3 py-2 rounded text-sm font-medium transition-colors flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          Next
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Frames View */}
              {viewMode === 'frames' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {searchResults.map((result, index) => (
                    <div
                      key={index}
                      className="bg-card rounded-lg border border-border p-4 hover:bg-muted/50 transition-all duration-300 cursor-pointer group"
                      onClick={() => onTimeJump(result.timestamp)}
                    >
                      <div className="flex gap-4">
                        {/* Frame Number & Thumbnail */}
                        <div className="flex flex-col items-center gap-2 flex-shrink-0">
                          <div className="w-20 h-12 bg-muted rounded flex items-center justify-center relative overflow-hidden">
                            {result.frame_path ? (
                              <img
                                src={`http://localhost:8001${result.frame_path}`}
                                alt={`Frame at ${formatTime(result.timestamp)}`}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  const target = e.currentTarget as HTMLImageElement;
                                  target.style.display = 'none';
                                  const fallback = target.nextElementSibling as HTMLElement;
                                  if (fallback) fallback.style.display = 'flex';
                                }}
                              />
                            ) : null}
                            <div
                              className="w-full h-full flex items-center justify-center"
                              style={{ display: result.frame_path ? 'none' : 'flex' }}
                            >
                              <Eye className="w-6 h-6 text-muted-foreground" />
                            </div>
                          </div>
                          <span className="text-xs text-muted-foreground font-medium">#{index + 1}</span>
                        </div>

                        {/* Content */}
                        <div className="flex-1">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1 pr-2">
                              {/* Summary (concise) */}
                              {result.summary ? (
                                <p className="text-foreground text-sm font-medium mb-1">
                                  {result.summary}
                                </p>
                              ) : (
                                <p className="text-foreground text-sm leading-relaxed group-hover:text-muted-foreground transition-colors">
                                  {result.description}
                                </p>
                              )}

                              {/* Objects detected */}
                              {result.objects_detected && result.objects_detected.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-2">
                                  {result.objects_detected.slice(0, 3).map((obj, objIndex) => (
                                    <span
                                      key={objIndex}
                                      className="inline-block px-2 py-1 bg-muted rounded text-xs text-muted-foreground border border-border"
                                    >
                                      {obj}
                                    </span>
                                  ))}
                                  {result.objects_detected.length > 3 && (
                                    <span className="text-xs text-muted-foreground">
                                      +{result.objects_detected.length - 3} more
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-xs">
                              <span className={`font-medium px-2 py-1 rounded ${getConfidenceColor(result.confidence)} bg-muted`}>
                                {result.confidence}%
                              </span>
                            </div>
                          </div>

                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <Clock className="w-3 h-3" />
                              <span className="font-medium">{formatTime(result.timestamp)}</span>
                              {result.people_count !== undefined && (
                                <>
                                  <span className="mx-1">•</span>
                                  <Users className="w-3 h-3" />
                                  <span>{result.people_count} person{result.people_count !== 1 ? 's' : ''}</span>
                                </>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              {/* Expand/Collapse detailed analysis */}
                              {result.detailed_analysis && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    toggleExpandResult(index);
                                  }}
                                  className="opacity-0 group-hover:opacity-100 transition-opacity bg-muted hover:bg-accent text-muted-foreground hover:text-accent-foreground px-2 py-1 rounded text-xs font-medium flex items-center gap-1"
                                >
                                  {expandedResults.has(index) ? (
                                    <>
                                      <ChevronUp className="w-3 h-3" />
                                      Less
                                    </>
                                  ) : (
                                    <>
                                      <ChevronDown className="w-3 h-3" />
                                      Details
                                    </>
                                  )}
                                </button>
                              )}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onTimeJump(result.timestamp);
                                }}
                                className="opacity-0 group-hover:opacity-100 transition-opacity bg-primary hover:bg-primary/90 text-primary-foreground px-3 py-1 rounded text-xs font-medium flex items-center gap-1"
                              >
                                <Eye className="w-3 h-3" />
                                Jump to frame
                              </button>
                            </div>
                          </div>

                          {/* Expanded detailed analysis */}
                          {expandedResults.has(index) && result.detailed_analysis && (
                            <div className="mt-3 pt-3 border-t border-border">
                              <p className="text-sm text-muted-foreground leading-relaxed">
                                {result.detailed_analysis}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <div className="max-w-md mx-auto">
                <Search className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                <h3 className="text-lg font-medium text-foreground">
                  No matches found for "{searchQuery}"
                </h3>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default VisualSearch;