import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import WiFiStatus from './WiFiStatus';
import StatusPanel from './StatusPanel';

function Dashboard() {
  const [systemStatus, setSystemStatus] = useState({
    localAudio: 'unknown',
    localCamera: 'unknown',
    localTopGamer: 'unknown',
    cloudAudio: 'unknown',
    cloudCamera: 'unknown',
    cloud: 'unknown',
    apiConnection: 'unknown',
    slamMode: 'unknown',
    navigationMode: 'unknown'
  });

  return (
    <div className="dashboard">
      <div className="dashboard-layout">
        {/* Left Panel - Status */}
        <div className="left-panel">
          <StatusPanel status={systemStatus} />
        </div>

        {/* Right Panel - WiFi */}
        <div className="right-panel">
          <WiFiStatus />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
