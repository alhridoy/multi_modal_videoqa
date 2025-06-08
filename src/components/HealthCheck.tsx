import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { apiService } from '@/services/api';

interface HealthStatus {
  status: 'healthy' | 'unhealthy' | 'checking';
  services?: Record<string, string>;
  error?: string;
}

const HealthCheck: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus>({ status: 'checking' });
  const [lastCheck, setLastCheck] = useState<Date | null>(null);

  const checkHealth = async () => {
    setHealth({ status: 'checking' });
    
    try {
      const response = await apiService.healthCheck();
      setHealth({
        status: 'healthy',
        services: response.services
      });
      setLastCheck(new Date());
    } catch (error) {
      setHealth({
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      setLastCheck(new Date());
    }
  };

  useEffect(() => {
    checkHealth();
    
    // Check health every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = () => {
    switch (health.status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'unhealthy':
        return <XCircle className="w-5 h-5 text-red-400" />;
      case 'checking':
        return <RefreshCw className="w-5 h-5 text-blue-400 animate-spin" />;
    }
  };

  const getStatusColor = () => {
    switch (health.status) {
      case 'healthy':
        return 'border-green-400 bg-green-400/10';
      case 'unhealthy':
        return 'border-red-400 bg-red-400/10';
      case 'checking':
        return 'border-blue-400 bg-blue-400/10';
    }
  };

  return (
    <div className={`fixed top-4 right-4 p-3 rounded-lg border backdrop-blur-lg ${getStatusColor()} z-50`}>
      <div className="flex items-center gap-2 mb-2">
        {getStatusIcon()}
        <span className="text-sm font-medium text-white">
          Backend Status
        </span>
        <button
          onClick={checkHealth}
          className="text-white/60 hover:text-white transition-colors"
          disabled={health.status === 'checking'}
        >
          <RefreshCw className={`w-4 h-4 ${health.status === 'checking' ? 'animate-spin' : ''}`} />
        </button>
      </div>
      
      {health.status === 'healthy' && health.services && (
        <div className="space-y-1">
          {Object.entries(health.services).map(([service, status]) => (
            <div key={service} className="flex items-center gap-2 text-xs">
              <div className={`w-2 h-2 rounded-full ${
                status === 'connected' || status === 'available' || status === 'ready' 
                  ? 'bg-green-400' 
                  : 'bg-yellow-400'
              }`} />
              <span className="text-white/80 capitalize">{service}</span>
              <span className="text-white/60">{status}</span>
            </div>
          ))}
        </div>
      )}
      
      {health.status === 'unhealthy' && (
        <div className="flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-xs text-red-200 mb-1">Backend Unavailable</p>
            <p className="text-xs text-red-300">{health.error}</p>
            <p className="text-xs text-red-400 mt-1">
              Make sure the backend is running on port 8002
            </p>
          </div>
        </div>
      )}
      
      {lastCheck && (
        <p className="text-xs text-white/50 mt-2">
          Last check: {lastCheck.toLocaleTimeString()}
        </p>
      )}
    </div>
  );
};

export default HealthCheck;
