import React, { useState, useEffect } from 'react';
import { TrendingUp, Users, Eye, Clock, BarChart3, Activity } from 'lucide-react';

interface TemporalData {
  timestamp: number;
  count: number;
  confidence: number;
  description: string;
}

interface TemporalCounterProps {
  videoId: number;
  query: string;
  data: TemporalData[];
  onTimeJump: (time: number) => void;
}

export const TemporalCounter: React.FC<TemporalCounterProps> = ({
  videoId,
  query,
  data,
  onTimeJump
}) => {
  const [selectedTimeRange, setSelectedTimeRange] = useState<[number, number] | null>(null);
  const [aggregationMode, setAggregationMode] = useState<'total' | 'average' | 'peak'>('total');

  // Calculate temporal statistics
  const calculateStats = () => {
    if (!data.length) return null;

    const totalCount = data.reduce((sum, item) => sum + item.count, 0);
    const averageCount = totalCount / data.length;
    const peakCount = Math.max(...data.map(item => item.count));
    const peakTimestamp = data.find(item => item.count === peakCount)?.timestamp || 0;
    
    return {
      total: totalCount,
      average: Math.round(averageCount * 10) / 10,
      peak: peakCount,
      peakTimestamp,
      dataPoints: data.length
    };
  };

  const stats = calculateStats();

  // Format time for display
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Generate timeline visualization
  const generateTimeline = () => {
    if (!data.length) return [];

    const maxCount = Math.max(...data.map(item => item.count));
    const timelineWidth = 400; // pixels
    const maxTimestamp = Math.max(...data.map(item => item.timestamp));

    return data.map((item, index) => {
      const x = (item.timestamp / maxTimestamp) * timelineWidth;
      const height = maxCount > 0 ? (item.count / maxCount) * 60 : 0; // max 60px height
      
      return {
        ...item,
        x,
        height,
        index
      };
    });
  };

  const timelineData = generateTimeline();

  return (
    <div className="bg-gray-900/80 rounded-lg border border-gray-700 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="text-white font-medium">Temporal Counting</h3>
            <p className="text-sm text-gray-400">"{query}" over time</p>
          </div>
        </div>
        
        {/* Aggregation Mode Selector */}
        <div className="flex items-center gap-2">
          {(['total', 'average', 'peak'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setAggregationMode(mode)}
              className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                aggregationMode === mode
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
              }`}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800/60 rounded-lg p-3 border border-gray-600">
            <div className="flex items-center gap-2 mb-1">
              <BarChart3 className="w-4 h-4 text-blue-400" />
              <span className="text-xs text-gray-400">Total</span>
            </div>
            <div className="text-lg font-bold text-white">{stats.total}</div>
          </div>
          
          <div className="bg-gray-800/60 rounded-lg p-3 border border-gray-600">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-4 h-4 text-green-400" />
              <span className="text-xs text-gray-400">Average</span>
            </div>
            <div className="text-lg font-bold text-white">{stats.average}</div>
          </div>
          
          <div className="bg-gray-800/60 rounded-lg p-3 border border-gray-600">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-orange-400" />
              <span className="text-xs text-gray-400">Peak</span>
            </div>
            <div className="text-lg font-bold text-white">{stats.peak}</div>
          </div>
          
          <div className="bg-gray-800/60 rounded-lg p-3 border border-gray-600">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-4 h-4 text-purple-400" />
              <span className="text-xs text-gray-400">Peak Time</span>
            </div>
            <div 
              className="text-lg font-bold text-white cursor-pointer hover:text-blue-400 transition-colors"
              onClick={() => onTimeJump(stats.peakTimestamp)}
            >
              {formatTime(stats.peakTimestamp)}
            </div>
          </div>
        </div>
      )}

      {/* Timeline Visualization */}
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-300 mb-3">Temporal Distribution</h4>
        <div className="relative bg-gray-800/40 rounded-lg p-4 border border-gray-600">
          {/* Timeline bars */}
          <div className="relative h-16 flex items-end justify-start gap-1">
            {timelineData.map((item, index) => (
              <div
                key={index}
                className="relative group cursor-pointer"
                style={{ left: `${item.x}px` }}
                onClick={() => onTimeJump(item.timestamp)}
              >
                {/* Bar */}
                <div
                  className={`w-2 bg-gradient-to-t transition-all duration-200 rounded-t ${
                    item.count > 0
                      ? 'from-blue-600 to-blue-400 hover:from-blue-500 hover:to-blue-300'
                      : 'from-gray-600 to-gray-500'
                  }`}
                  style={{ height: `${item.height}px` }}
                />
                
                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity bg-black text-white text-xs rounded px-2 py-1 whitespace-nowrap z-10">
                  <div className="font-medium">{formatTime(item.timestamp)}</div>
                  <div>Count: {item.count}</div>
                  <div>Confidence: {Math.round(item.confidence * 100)}%</div>
                </div>
              </div>
            ))}
          </div>
          
          {/* Time axis */}
          <div className="flex justify-between text-xs text-gray-500 mt-2">
            <span>0:00</span>
            <span>{formatTime(Math.max(...data.map(item => item.timestamp)))}</span>
          </div>
        </div>
      </div>

      {/* Detailed Data Table */}
      <div className="max-h-48 overflow-y-auto">
        <h4 className="text-sm font-medium text-gray-300 mb-3">Detailed Breakdown</h4>
        <div className="space-y-2">
          {data.map((item, index) => (
            <div
              key={index}
              className="flex items-center justify-between bg-gray-800/40 rounded-lg p-3 border border-gray-600 hover:bg-gray-700/40 transition-colors cursor-pointer"
              onClick={() => onTimeJump(item.timestamp)}
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-blue-600/20 rounded-full flex items-center justify-center">
                  <span className="text-xs font-bold text-blue-400">{item.count}</span>
                </div>
                <div>
                  <div className="text-sm font-medium text-white">
                    {formatTime(item.timestamp)}
                  </div>
                  <div className="text-xs text-gray-400 truncate max-w-48">
                    {item.description}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <div className="text-xs text-gray-400">
                  {Math.round(item.confidence * 100)}%
                </div>
                <Eye className="w-4 h-4 text-gray-400 hover:text-white transition-colors" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Summary */}
      <div className="mt-4 pt-4 border-t border-gray-600">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">
            Analyzed {stats?.dataPoints || 0} time points
          </span>
          <span className="text-gray-400">
            {aggregationMode === 'total' && `Total: ${stats?.total || 0}`}
            {aggregationMode === 'average' && `Avg: ${stats?.average || 0}`}
            {aggregationMode === 'peak' && `Peak: ${stats?.peak || 0} at ${formatTime(stats?.peakTimestamp || 0)}`}
          </span>
        </div>
      </div>
    </div>
  );
};
