const API_BASE_URL = 'http://localhost:8002/api/v1';

export interface VideoInfo {
  id: number;
  title: string;
  url: string;
  video_type: string;
  status: string;
  duration?: number;
  has_transcript: boolean;
  sections?: VideoSection[];
  frame_count: number;
  created_at: string;
}

export interface VideoSection {
  id: number;
  title: string;
  start_time: number;
  end_time: number;
  description: string;
  key_topics: string[];
}

export interface ChatMessage {
  id: number;
  message: string;
  response: string;
  citations: Citation[];
  created_at: string;
}

export interface Citation {
  text: string;
  time: number;
  timestamp: string;
  citation_id: number;
}

export interface SearchResult {
  timestamp: number;
  confidence: number;
  description: string;
  frame_path: string;
  summary?: string;
  objects_detected?: string[];
  people_count?: number;
  detailed_analysis?: string;
}

export interface ClipResult {
  start_time: number;
  end_time: number;
  confidence: number;
  description: string;
  frame_count: number;
  frames: SearchResult[];
  thumbnail_url?: string;
}

export interface VideoClip {
  start_time: number;
  end_time: number;
  confidence: number;
  description: string;
  frame_count: number;
}

export interface VisualSearchResponse {
  query: string;
  results: SearchResult[];
  clips: ClipResult[];
  total_results: number;
  direct_answer?: string;
  query_type?: string;
  processing_method?: string;
}

export interface SearchSuggestionsResponse {
  video_id: number;
  suggestions: string[];
  categories: {
    objects: string[];
    people: string[];
    scenes: string[];
    text: string[];
    actions: string[];
    colors: string[];
  };
  total_suggestions: number;
  generation_method: string;
}

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Video endpoints
  async uploadVideo(file: File): Promise<{ video_id: number; status: string; message: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/video/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async processYouTubeVideo(youtubeUrl: string): Promise<{
    video_id: number;
    status: string;
    title: string;
    has_transcript: boolean;
    sections_count: number;
  }> {
    return this.request('/video/youtube', {
      method: 'POST',
      body: JSON.stringify({ youtube_url: youtubeUrl }),
    });
  }

  async getVideo(videoId: number): Promise<VideoInfo> {
    return this.request(`/video/${videoId}`);
  }

  async getVideoSections(videoId: number): Promise<{ video_id: number; sections: VideoSection[] }> {
    return this.request(`/video/${videoId}/sections`);
  }

  async deleteVideo(videoId: number): Promise<{ message: string }> {
    return this.request(`/video/${videoId}`, {
      method: 'DELETE',
    });
  }

  // Chat endpoints
  async sendChatMessage(videoId: number, message: string): Promise<{
    response: string;
    citations: Citation[];
    message_id: number;
  }> {
    return this.request('/chat/message', {
      method: 'POST',
      body: JSON.stringify({
        video_id: videoId,
        message,
      }),
    });
  }

  async getChatHistory(videoId: number, limit: number = 50): Promise<{
    video_id: number;
    messages: ChatMessage[];
  }> {
    return this.request(`/chat/${videoId}/history?limit=${limit}`);
  }

  async clearChatHistory(videoId: number): Promise<{ message: string; video_id: number }> {
    return this.request(`/chat/${videoId}/history`, {
      method: 'DELETE',
    });
  }

  // Search endpoints
  async visualSearch(videoId: number, query: string, maxResults: number = 10, useNative: boolean = true): Promise<VisualSearchResponse> {
    const searchUrl = useNative ? '/search/visual?use_native=true' : '/search/visual?use_native=false';
    return this.request(searchUrl, {
      method: 'POST',
      body: JSON.stringify({
        video_id: videoId,
        query,
        max_results: maxResults,
      }),
    });
  }

  async getNativeVisualSearch(videoId: number, query: string, maxResults: number = 10): Promise<VisualSearchResponse> {
    return this.request('/search/native', {
      method: 'POST',
      body: JSON.stringify({
        video_id: videoId,
        query,
        max_results: maxResults,
      }),
    });
  }

  async getVideoFrame(videoId: number, timestamp: number): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/video/${videoId}/frame/${timestamp}`);
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Frame fetch failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    
    return response.blob();
  }

  async getVideoFrames(videoId: number, limit: number = 50): Promise<{
    video_id: number;
    frames: Array<{
      id: number;
      timestamp: number;
      frame_path: string;
      description?: string;
      objects_detected?: any;
    }>;
  }> {
    return this.request(`/search/${videoId}/frames?limit=${limit}`);
  }

  async analyzeVideoFrames(videoId: number): Promise<{
    message: string;
    analyzed_count: number;
    total_frames: number;
  }> {
    return this.request(`/search/${videoId}/analyze-frames`, {
      method: 'POST',
    });
  }

  async getSearchSuggestions(videoId: number): Promise<SearchSuggestionsResponse> {
    return this.request(`/search/${videoId}/suggestions`);
  }

  // Health check
  async healthCheck(): Promise<{ status: string; services: Record<string, string> }> {
    // Health endpoint is at root level, not under /api/v1
    const url = 'http://localhost:8002/health';

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Health check failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }
}

export const apiService = new ApiService();
