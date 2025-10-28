import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './StatusPanel.css';

const API_BASE = '/api';

function StatusPanel({ status }) {
  const [streamsData, setStreamsData] = useState(null);
  const [containerRunning, setContainerRunning] = useState(false);

  // Fetch streams status
  const fetchStreamsStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/streams/status`);
      if (response.data.success) {
        setStreamsData(response.data.data.streams);
        setContainerRunning(response.data.data.container_running);
      }
    } catch (error) {
      console.error('Failed to fetch streams status:', error);
      setStreamsData(null);
      setContainerRunning(false);
    }
  };

  // Auto-refresh every 5 seconds
  useEffect(() => {
    fetchStreamsStatus();
    const interval = setInterval(fetchStreamsStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIndicator = (stream) => {
    if (!stream) return <span className="status-dot status-unknown"></span>;
    
    switch (stream.status) {
      case 'running':
        // Check if RTSP stream is actually streaming
        if (stream.rtsp_streaming === false) {
          return <span className="status-dot status-warning"></span>;
        }
        return <span className="status-dot status-running"></span>;
      case 'running_no_stream':
        return <span className="status-dot status-warning"></span>;
      case 'stopped':
        return <span className="status-dot status-stopped"></span>;
      case 'not_configured':
        return <span className="status-dot status-not-configured"></span>;
      case 'unavailable':
        return <span className="status-dot status-unavailable"></span>;
      default:
        return <span className="status-dot status-unknown"></span>;
    }
  };

  const getStatusText = (stream) => {
    if (!containerRunning) return 'Container not running';
    if (!stream) return 'Unknown';
    
    switch (stream.status) {
      case 'running':
        if (stream.rtsp_streaming === false) {
          return 'Running (no stream)';
        }
        return stream.rtsp_streaming ? 'Running & Streaming' : 'Running';
      case 'running_no_stream':
        return 'Running (no stream)';
      case 'stopped':
        return 'Stopped';
      case 'not_configured':
        return 'Not configured';
      case 'unavailable':
        return 'Unavailable';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="status-panel">
      <h2>Status</h2>
      <div className="status-list">
        <div className="status-item">
          {getStatusIndicator(streamsData?.audio)}
          <span className="status-label">Local audio status</span>
          <span className="status-value">{getStatusText(streamsData?.audio)}</span>
        </div>
        <div className="status-item">
          {getStatusIndicator(streamsData?.top_camera)}
          <span className="status-label">Local front camera status</span>
          <span className="status-value">{getStatusText(streamsData?.top_camera)}</span>
        </div>
        <div className="status-item">
          <span className="status-dot status-unknown"></span>
          <span className="status-label">Local top gamer</span>
          <span className="status-value">Not implemented</span>
        </div>
        
        <div className="status-divider"></div>
        
        <div className="status-item">
          <span className="status-dot status-unknown"></span>
          <span className="status-label">Cloud audio..</span>
          <span className="status-value">Not implemented</span>
        </div>
        <div className="status-item">
          <span className="status-dot status-unknown"></span>
          <span className="status-label">Cloud camera</span>
          <span className="status-value">Not implemented</span>
        </div>
        <div className="status-item">
          <span className="status-dot status-unknown"></span>
          <span className="status-label">cloud ..</span>
          <span className="status-value">Not implemented</span>
        </div>
        
        <div className="status-divider"></div>
        
        <div className="status-item">
          <span className="status-dot status-unknown"></span>
          <span className="status-label">api.openmind.org connection</span>
          <span className="status-value">Not implemented</span>
        </div>
        
        <div className="status-divider"></div>
        
        <div className="status-item">
          <span className="status-dot status-unknown"></span>
          <span className="status-label">SLAM Mode</span>
          <span className="status-value">Not implemented</span>
        </div>
        <div className="status-item">
          <span className="status-dot status-unknown"></span>
          <span className="status-label">Navigation Mode</span>
          <span className="status-value">Not implemented</span>
        </div>
      </div>
    </div>
  );
}

export default StatusPanel;
