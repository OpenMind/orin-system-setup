import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Wifi, WifiOff, Loader, AlertCircle } from 'lucide-react';

const API_BASE = '/api';

function WiFiStatus() {
  const [wifiStatus, setWifiStatus] = useState(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [showConnectForm, setShowConnectForm] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [ssid, setSsid] = useState('');
  const [password, setPassword] = useState('');
  const [connectionResult, setConnectionResult] = useState(null);

  // Fetch WiFi status
  const fetchWiFiStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/wifi/status`);
      if (response.data.success) {
        setWifiStatus(response.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch WiFi status:', error);
    } finally {
      setInitialLoading(false);
    }
  };

  const resetForm = () => {
    setSsid('');
    setPassword('');
    setShowConnectForm(false);
    setConnectionResult(null);
  };

  const connectToNetwork = async () => {
    if (!ssid.trim()) {
      setConnectionResult({
        success: false,
        message: 'Please enter a WiFi network name'
      });
      return;
    }
    
    setConnecting(true);
    setConnectionResult(null);
    
    try {
      const response = await axios.post(`${API_BASE}/wifi/connect`, {
        ssid: ssid.trim(),
        password: password
      });
      
      // Response from async connection
      if (response.data.status === 'connecting') {
        setConnectionResult({
          success: true,
          message: `Connecting to ${ssid.trim()}...`,
          instructions: ['This will take 15-20 seconds', 'Your device will disconnect from hotspot']
        });
        
        // Reset form after showing result
        setTimeout(resetForm, 8000);
      } else {
        setConnectionResult({
          success: false,
          message: response.data.error || 'Connection failed'
        });
      }
    } catch (error) {
      console.error('Connection failed:', error);
      setConnectionResult({
        success: false,
        message: error.response?.data?.error || 'Network error - please try again'
      });
    } finally {
      setConnecting(false);
    }
  };

  // Auto-refresh status every 5 seconds
  useEffect(() => {
    fetchWiFiStatus();
    const interval = setInterval(fetchWiFiStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  if (initialLoading) {
    return (
      <div className="bg-white rounded-2xl p-8 shadow-sm flex flex-col gap-5">
        <div className="flex justify-between items-center pb-5 border-b border-gray-200">
          <div className="flex items-center gap-4 animate-pulse">
            <div className="w-6 h-6 bg-gray-200 rounded-full"></div>
            <div>
              <div className="h-3.5 bg-gray-200 rounded w-20 mb-2"></div>
              <div className="h-3.5 bg-gray-200 rounded w-28"></div>
            </div>
          </div>
          <div className="h-10 w-28 bg-gray-200 rounded-lg animate-pulse"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl p-8 shadow-sm flex flex-col gap-5">
      {/* Header */}
      <div className="flex justify-between items-center pb-5 border-b border-gray-200">
        <div className="flex items-center gap-4">
          {wifiStatus?.connected ? (
            <Wifi className="text-green-500" size={24} />
          ) : (
            <WifiOff className="text-orange-500" size={24} />
          )}
          <div>
            <div className="text-sm text-slate-600 mb-1">WiFi Status</div>
            <div className="text-base font-semibold text-slate-800">
              {wifiStatus?.connected ? wifiStatus.ssid : 'Hotspot Mode'}
            </div>
          </div>
        </div>
        {!showConnectForm && !connectionResult && (
          <button 
            className="px-5 py-2.5 bg-blue-500 text-white border-none rounded-lg font-medium text-sm cursor-pointer transition-all hover:bg-blue-600 flex items-center gap-2" 
            onClick={() => setShowConnectForm(true)}
          >
            Connect WiFi
          </button>
        )}
      </div>

      {/* Info Banner */}
      {!wifiStatus?.connected && !showConnectForm && !connectionResult && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="text-blue-600 flex-shrink-0 mt-0.5" size={20} />
            <div className="text-sm text-blue-800">
              <p className="font-medium">You are connected to the setup hotspot</p>
              <p className="text-blue-700 mt-1">Click "Connect WiFi" to connect this device to a WiFi network.</p>
            </div>
          </div>
        </div>
      )}

      {/* Connection Form */}
      {showConnectForm && !connectionResult && (
        <div className="flex flex-col gap-4">
          <h3 className="text-base font-semibold text-slate-800">Connect to WiFi Network</h3>
          
          <div className="flex flex-col gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Network Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                className="w-full px-4 py-3 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="WiFi network name"
                value={ssid}
                onChange={(e) => setSsid(e.target.value)}
                autoFocus
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Password
              </label>
              <input
                type="password"
                className="w-full px-4 py-3 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="WiFi password (optional for open networks)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && connectToNetwork()}
              />
            </div>

            <div className="flex gap-2 mt-2">
              <button 
                className="flex-1 px-4 py-2.5 bg-slate-100 text-slate-700 border-none rounded-lg font-medium text-sm cursor-pointer transition-colors hover:bg-slate-200"
                onClick={resetForm}
                disabled={connecting}
              >
                Cancel
              </button>
              <button 
                className="flex-1 px-4 py-2.5 bg-green-600 text-white border-none rounded-lg font-medium text-sm cursor-pointer transition-colors hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                onClick={connectToNetwork}
                disabled={connecting || !ssid.trim()}
              >
                {connecting && <Loader className="animate-spin" size={16} />}
                {connecting ? 'Connecting...' : 'Connect'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Connection Result */}
      {connectionResult && (
        <div className={`rounded-lg p-5 ${connectionResult.success ? 'bg-blue-50 border border-blue-200' : 'bg-red-50 border border-red-200'}`}>
          <div className="flex items-start gap-3">
            {connectionResult.success ? (
              <Loader className="text-blue-600 flex-shrink-0 mt-0.5 animate-spin" size={24} />
            ) : (
              <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" size={24} />
            )}
            <div className="flex-1">
              <h4 className={`font-semibold mb-2 ${connectionResult.success ? 'text-blue-800' : 'text-red-800'}`}>
                {connectionResult.message}
              </h4>
              {connectionResult.success && connectionResult.instructions && (
                <ul className="text-sm text-blue-700 space-y-1">
                  {connectionResult.instructions.map((instruction, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-blue-500 mt-0.5">•</span>
                      <span>{instruction}</span>
                    </li>
                  ))}
                </ul>
              )}
              {!connectionResult.success && (
                <div className="flex gap-2 mt-3">
                  <button
                    className="px-4 py-2 bg-red-600 text-white border-none rounded-lg font-medium text-sm cursor-pointer transition-colors hover:bg-red-700"
                    onClick={() => {
                      setConnectionResult(null);
                      setShowConnectForm(true);
                    }}
                  >
                    Try Again
                  </button>
                  <button
                    className="px-4 py-2 bg-slate-100 text-slate-700 border-none rounded-lg font-medium text-sm cursor-pointer transition-colors hover:bg-slate-200"
                    onClick={resetForm}
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default WiFiStatus;
