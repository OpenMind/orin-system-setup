import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Wifi, WifiOff, RefreshCw, Loader } from 'lucide-react';
import './WiFiStatus.css';

const API_BASE = '/api';

function WiFiStatus() {
  const [wifiStatus, setWifiStatus] = useState(null);
  const [networks, setNetworks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [showNetworkList, setShowNetworkList] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [selectedNetwork, setSelectedNetwork] = useState(null);
  const [password, setPassword] = useState('');

  // Fetch WiFi status
  const fetchWiFiStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/wifi/status`);
      if (response.data.success) {
        setWifiStatus(response.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch WiFi status:', error);
    }
  };

  // Scan for networks
  const scanNetworks = async () => {
    setScanning(true);
    try {
      const response = await axios.get(`${API_BASE}/wifi/networks`);
      if (response.data.success) {
        setNetworks(response.data.data);
        setShowNetworkList(true);
      }
    } catch (error) {
      console.error('Failed to scan networks:', error);
    } finally {
      setScanning(false);
    }
  };

  // Connect to network
  const connectToNetwork = async () => {
    if (!selectedNetwork) return;
    
    setConnecting(true);
    try {
      const response = await axios.post(`${API_BASE}/wifi/connect`, {
        ssid: selectedNetwork.ssid,
        password: password
      });
      
      if (response.data.success) {
        setSelectedNetwork(null);
        setPassword('');
        setShowNetworkList(false);
        await fetchWiFiStatus();
      } else {
        alert(response.data.message || 'Failed to connect');
      }
    } catch (error) {
      console.error('Connection failed:', error);
      alert('Failed to connect to network');
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

  const getSignalIcon = (signal) => {
    if (signal >= 75) return '▂▄▆█';
    if (signal >= 50) return '▂▄▆';
    if (signal >= 25) return '▂▄';
    return '▂';
  };

  return (
    <div className="wifi-status">
      <div className="wifi-header">
        <div className="wifi-title">
          {wifiStatus?.connected ? (
            <Wifi className="icon-wifi" size={24} />
          ) : (
            <WifiOff className="icon-wifi-off" size={24} />
          )}
          <div>
            <div className="status-label">WiFi status</div>
            <div className="status-value">
              {wifiStatus?.connected ? wifiStatus.ssid : 'Not connected'}
            </div>
          </div>
        </div>
        <button 
          className="btn-change" 
          onClick={scanNetworks}
          disabled={scanning}
        >
          {scanning ? <Loader className="spin" size={16} /> : null}
          Change WIFI
        </button>
      </div>

      {showNetworkList && (
        <div className="network-list">
          <div className="network-list-header">
            <h3>Available Networks</h3>
            <button 
              className="btn-refresh" 
              onClick={scanNetworks}
              disabled={scanning}
            >
              <RefreshCw className={scanning ? 'spin' : ''} size={16} />
            </button>
          </div>

          {networks.length === 0 ? (
            <div className="no-networks">
              {scanning ? 'Scanning...' : 'No networks found'}
            </div>
          ) : (
            <div className="networks">
              {networks.map((network, index) => (
                <div 
                  key={index}
                  className={`network-item ${network.connected ? 'connected' : ''} ${selectedNetwork?.ssid === network.ssid ? 'selected' : ''}`}
                  onClick={() => setSelectedNetwork(network)}
                >
                  <div className="network-info">
                    <div className="network-ssid">{network.ssid}</div>
                    <div className="network-details">
                      <span className="signal">{getSignalIcon(network.signal)}</span>
                      <span className="security">{network.security}</span>
                    </div>
                  </div>
                  {network.connected && (
                    <span className="badge-connected">Connected</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {selectedNetwork && !selectedNetwork.connected && (
            <div className="connect-form">
              <input
                type="password"
                className="input-password"
                placeholder={`Password for ${selectedNetwork.ssid}`}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && connectToNetwork()}
              />
              <div className="connect-actions">
                <button 
                  className="btn-cancel"
                  onClick={() => {
                    setSelectedNetwork(null);
                    setPassword('');
                  }}
                >
                  Cancel
                </button>
                <button 
                  className="btn-connect"
                  onClick={connectToNetwork}
                  disabled={connecting}
                >
                  {connecting ? <Loader className="spin" size={16} /> : null}
                  {connecting ? 'Connecting...' : 'Connect'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default WiFiStatus;
