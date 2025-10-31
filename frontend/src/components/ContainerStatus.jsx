import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, Server, Cpu, AlertCircle, CheckCircle2, XCircle, Circle } from 'lucide-react';

const ContainerStatus = () => {
  const [containersData, setContainersData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchContainerStatus = async () => {
    try {
      const response = await axios.get('/api/containers/status');
      if (response.data.success) {
        setContainersData(response.data.data);
        setError(null);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContainerStatus();
    const interval = setInterval(fetchContainerStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status) => {
    if (status?.running) {
      return <CheckCircle2 size={16} style={{ color: '#10b981' }} />;
    }
    return <XCircle size={16} style={{ color: '#ef4444' }} />;
  };

  const getStreamStatusIcon = (status) => {
    if (status === 'running') {
      return <Circle size={12} style={{ color: '#10b981', fill: '#10b981' }} />;
    }
    return <Circle size={12} style={{ color: '#ef4444', fill: '#ef4444' }} />;
  };

  const getStatusText = (status) => {
    if (!status) return 'Unknown';
    if (status.running) return 'Running';
    if (status.status === 'not_found') return 'Not Found';
    return 'Stopped';
  };

  const getStatusColor = (status) => {
    if (!status) return '#6b7280';
    if (status.running) return '#10b981';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="container-status">
        <h2>Container Status</h2>
        <div className="loading">Loading container information...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container-status">
        <h2>Container Status</h2>
        <div className="error-message">
          <AlertCircle size={20} />
          <span>Error: {error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container-status">
      <h2>
        <Server size={24} />
        Container Status
      </h2>

      <div className="container-list">
        {/* Video Processor */}
        <div className="container-section">
          <div className="section-header">
            <Activity size={18} />
            <span className="section-title">Video Processor</span>
            {getStatusIcon(containersData?.video_processor?.container_status)}
          </div>
          
          <div className="section-content">
            {/* Container Status */}
            <div className="status-item level-1">
              <span className="item-label">Container Status</span>
              <span className="item-value" style={{ 
                color: getStatusColor(containersData?.video_processor?.container_status) 
              }}>
                {getStatusText(containersData?.video_processor?.container_status)}
              </span>
            </div>

            {/* Local Streams */}
            {containersData?.video_processor?.local_streams?.length > 0 && (
              <>
                <div className="status-item level-1">
                  <span className="item-label">Local Streams</span>
                </div>
                {containersData.video_processor.local_streams.map((stream, idx) => (
                  <div key={idx} className="status-item level-2">
                    {getStreamStatusIcon(stream.status)}
                    <span className="item-label">{stream.name}</span>
                    <span className="item-value">{stream.status}</span>
                  </div>
                ))}
              </>
            )}

            {/* Cloud Streams */}
            {containersData?.video_processor?.cloud_streams?.length > 0 && (
              <>
                <div className="status-item level-1">
                  <span className="item-label">Cloud Streams</span>
                </div>
                {containersData.video_processor.cloud_streams.map((stream, idx) => (
                  <div key={idx} className="status-item level-2">
                    {getStreamStatusIcon(stream.status)}
                    <span className="item-label">{stream.name}</span>
                    <span className="item-value">{stream.status}</span>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>

        {/* ROS2 Sensor */}
        <div className="container-section">
          <div className="section-header">
            <Cpu size={18} />
            <span className="section-title">ROS2 Sensor</span>
            {getStatusIcon(containersData?.ros2_sensor?.container_status)}
          </div>
          
          <div className="section-content">
            {/* Container Status */}
            <div className="status-item level-1">
              <span className="item-label">Container Status</span>
              <span className="item-value" style={{ 
                color: getStatusColor(containersData?.ros2_sensor?.container_status) 
              }}>
                {getStatusText(containersData?.ros2_sensor?.container_status)}
              </span>
            </div>

            {/* Local Camera Streams */}
            {containersData?.ros2_sensor?.local_streams?.length > 0 && (
              <>
                <div className="status-item level-1">
                  <span className="item-label">Local Camera Streams</span>
                </div>
                {containersData.ros2_sensor.local_streams.map((stream, idx) => (
                  <div key={idx} className="status-item level-2">
                    {getStreamStatusIcon(stream.status)}
                    <span className="item-label">{stream.name}</span>
                    <span className="item-value">{stream.status}</span>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>

        {/* Orchestrator */}
        <div className="container-section">
          <div className="section-header">
            <Server size={18} />
            <span className="section-title">Orchestrator</span>
            {getStatusIcon(containersData?.orchestrator?.container_status)}
          </div>
          
          <div className="section-content">
            {/* Container Status */}
            <div className="status-item level-1">
              <span className="item-label">Container Status</span>
              <span className="item-value" style={{ 
                color: getStatusColor(containersData?.orchestrator?.container_status) 
              }}>
                {getStatusText(containersData?.orchestrator?.container_status)}
              </span>
            </div>

            {/* Services */}
            {containersData?.orchestrator?.services && Object.keys(containersData.orchestrator.services).length > 0 && (
              <>
                <div className="status-item level-1">
                  <span className="item-label">SLAM Status</span>
                  <span className="item-value">{containersData.orchestrator.services.slam || 'unknown'}</span>
                </div>
                <div className="status-item level-1">
                  <span className="item-label">Nav2 Status</span>
                  <span className="item-value">{containersData.orchestrator.services.nav2 || 'unknown'}</span>
                </div>
                <div className="status-item level-1">
                  <span className="item-label">Charging Status</span>
                  <span className="item-value">
                    {containersData.orchestrator.services.is_charging ? 'Charging' : 'Not Charging'}
                    {containersData.orchestrator.services.battery_soc !== undefined && 
                      ` (${Math.round(containersData.orchestrator.services.battery_soc)}%)`}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <style jsx>{`
        .container-status {
          background: white;
          border-radius: 8px;
          padding: 24px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .container-status h2 {
          margin: 0 0 24px 0;
          font-size: 24px;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .loading, .error-message {
          padding: 20px;
          text-align: center;
          color: #6b7280;
        }

        .error-message {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          color: #ef4444;
        }

        .container-list {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .container-section {
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          overflow: hidden;
          background: white;
        }

        .section-header {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 14px 16px;
          background: #f9fafb;
          border-bottom: 1px solid #e5e7eb;
        }

        .section-title {
          flex: 1;
          font-size: 16px;
          font-weight: 600;
          color: #374151;
        }

        .section-content {
          padding: 8px 0;
        }

        .status-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 16px;
          transition: background 0.15s ease;
        }

        .status-item:hover {
          background: #f9fafb;
        }

        .status-item.level-1 {
          padding-left: 16px;
        }

        .status-item.level-2 {
          padding-left: 36px;
          background: #fafafa;
        }

        .status-item.level-2:hover {
          background: #f3f4f6;
        }

        .item-label {
          flex: 1;
          font-size: 14px;
          color: #6b7280;
        }

        .status-item.level-1 .item-label {
          font-weight: 500;
          color: #374151;
        }

        .item-value {
          font-size: 14px;
          font-weight: 500;
          color: #374151;
        }
      `}</style>
    </div>
  );
};

export default ContainerStatus;
