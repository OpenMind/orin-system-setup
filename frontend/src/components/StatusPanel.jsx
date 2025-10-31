import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = '/api';

function StatusPanel() {
  const [containersData, setContainersData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Fetch container status
  const fetchContainerStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/containers/status`);
      if (response.data.success) {
        setContainersData(response.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch container status:', error);
      setContainersData(null);
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh every 5 seconds
  useEffect(() => {
    fetchContainerStatus();
    const interval = setInterval(fetchContainerStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status) => {
    if (!status) return '#6b7280';
    if (status.running) return '#10b981';
    return '#ef4444';
  };

  const getStatusText = (status) => {
    if (!status) return 'Unknown';
    if (status.running) return 'Running';
    if (status.status === 'not_found') return 'Not Found';
    return 'Stopped';
  };

  // Reusable container status component
  const ContainerStatus = ({ title, containerData, streams = null, services = null, streamTitle = "Streams" }) => {
    const status = containerData?.container_status;
    
    return (
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3.5 bg-gray-50 border-b border-gray-200">
          <span className="text-[15px] font-semibold text-gray-700">{title}</span>
          <span className="text-[13px] font-medium" style={{ color: getStatusColor(status) }}>
            {getStatusText(status)}
          </span>
        </div>
        <div className="py-2">
          <div className="flex items-center justify-between px-4 py-2.5 transition-colors hover:bg-gray-50">
            <span className="text-sm font-medium text-gray-700">Container Status</span>
            <span className="text-sm font-medium text-gray-700" style={{ color: getStatusColor(status) }}>
              {getStatusText(status)}
            </span>
          </div>

          {/* Streams */}
          {streams && streams.length > 0 && (
            <>
              <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 font-semibold">
                <span className="text-sm font-semibold text-gray-700">{streamTitle}</span>
              </div>
              {streams.map((stream, idx) => (
                <div key={idx} className="flex items-center justify-between pl-9 pr-4 py-2.5 bg-gray-50/50 transition-colors hover:bg-gray-100">
                  <span className="text-sm text-gray-600">{stream.name}</span>
                  <span className="text-sm font-medium text-gray-700">{stream.status}</span>
                </div>
              ))}
            </>
          )}

          {/* Services */}
          {services && Object.keys(services).length > 0 && (
            <>
              {services.slam !== undefined && (
                <div className="flex items-center justify-between px-4 py-2.5 transition-colors hover:bg-gray-50">
                  <span className="text-sm font-medium text-gray-700">SLAM Status</span>
                  <span className="text-sm font-medium text-gray-700">{services.slam}</span>
                </div>
              )}
              {services.nav2 !== undefined && (
                <div className="flex items-center justify-between px-4 py-2.5 transition-colors hover:bg-gray-50">
                  <span className="text-sm font-medium text-gray-700">Nav2 Status</span>
                  <span className="text-sm font-medium text-gray-700">{services.nav2}</span>
                </div>
              )}
              {services.is_charging !== undefined && (
                <div className="flex items-center justify-between px-4 py-2.5 transition-colors hover:bg-gray-50">
                  <span className="text-sm font-medium text-gray-700">Charging Status</span>
                  <span className="text-sm font-medium text-gray-700">
                    {services.is_charging ? 'Charging' : 'Not Charging'}
                    {services.battery_soc !== undefined && ` (${Math.round(services.battery_soc)}%)`}
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-10 shadow-sm h-full">
        <h2 className="text-lg font-semibold mb-7 text-gray-900">Container Status</h2>
        <div className="flex flex-col gap-4">
          {/* Loading placeholders */}
          {[1, 2, 3].map((i) => (
            <div key={i} className="border border-gray-200 rounded-lg overflow-hidden animate-pulse">
              <div className="flex items-center justify-between p-3.5 bg-gray-50 border-b border-gray-200">
                <div className="h-4 bg-gray-200 rounded w-1/3"></div>
              </div>
              <div className="py-2">
                <div className="px-4 py-2.5">
                  <div className="h-3.5 bg-gray-200 rounded w-4/5"></div>
                </div>
                <div className="px-4 py-2.5">
                  <div className="h-3.5 bg-gray-200 rounded w-4/5"></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl p-10 shadow-sm h-full">
      <h2 className="text-lg font-semibold mb-7 text-gray-900">Container Status</h2>
      <div className="flex flex-col gap-4">
        <ContainerStatus 
          title="Video Processor"
          containerData={containersData?.video_processor}
          streams={containersData?.video_processor?.local_streams}
          streamTitle="Local Streams"
        />
        {containersData?.video_processor?.cloud_streams?.length > 0 && (
          <ContainerStatus 
            title="Video Processor - Cloud"
            containerData={containersData?.video_processor}
            streams={containersData?.video_processor?.cloud_streams}
            streamTitle="Cloud Streams"
          />
        )}
        <ContainerStatus 
          title="ROS2 Sensor"
          containerData={containersData?.ros2_sensor}
          streams={containersData?.ros2_sensor?.local_streams}
          streamTitle="Local Camera Streams"
        />
        <ContainerStatus 
          title="Orchestrator"
          containerData={containersData?.orchestrator}
          services={containersData?.orchestrator?.services}
        />
      </div>
    </div>
  );
}

export default StatusPanel;
