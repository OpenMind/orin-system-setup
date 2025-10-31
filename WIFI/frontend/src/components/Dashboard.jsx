import React from 'react';
import WiFiStatus from './WiFiStatus';
import StatusPanel from './StatusPanel';

function Dashboard() {
  return (
    <div className="min-h-screen p-5 bg-gray-50">
      <div className="max-w-7xl mx-auto mb-5">
        <h1 className="text-3xl font-bold text-gray-800">Orin System Monitor</h1>
      </div>
      
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-5 items-start">
        {/* Left Panel - Container Status */}
        <div className="flex flex-col">
          <StatusPanel />
        </div>

        {/* Right Panel - WiFi */}
        <div className="flex flex-col">
          <WiFiStatus />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
