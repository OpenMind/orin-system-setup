import subprocess
import time
import threading
import logging
from typing import Dict, Optional


class WiFiManager:    
    NMCLI = "/usr/bin/nmcli"
    
    def __init__(self, interface_name: str = "wlP1p1s0"):
        self.interface_name = interface_name
    
    def get_connection_status(self) -> Dict:
        """
        Get current WiFi connection status
        
        Returns:
            Dict with connection details
        """
        try:
            cmd = [self.NMCLI, "-t", "-f", "DEVICE,STATE,CONNECTION", "device", "status"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return {
                    'connected': False,
                    'ssid': None,
                    'interface': self.interface_name,
                    'error': result.stderr
                }
            
            # Parse output
            for line in result.stdout.strip().split('\n'):
                if self.interface_name in line:
                    parts = line.split(':')
                    if len(parts) >= 3:
                        device, state, connection = parts[0], parts[1], parts[2]
                        
                        is_connected = 'connected' in state.lower() and 'externally' not in state.lower()
                        
                        return {
                            'connected': is_connected,
                            'ssid': connection if is_connected and connection != '--' else None,
                            'interface': self.interface_name,
                            'state': state
                        }
            
            # Interface not found
            return {
                'connected': False,
                'ssid': None,
                'interface': self.interface_name,
                'state': 'not found'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'connected': False,
                'ssid': None,
                'interface': self.interface_name,
                'error': 'Command timeout'
            }
        except Exception as e:
            logging.error(f"Error getting connection status: {e}")
            return {
                'connected': False,
                'ssid': None,
                'interface': self.interface_name,
                'error': str(e)
            }
    
    def connect_wifi_async(self, ssid: str, password: str = '') -> Dict:
        """
        Connect to WiFi network asynchronously with hotspot management
        
        Args:
            ssid: Network SSID
            password: Network password (optional)
        
        Returns:
            Dict with connection status and instructions
        """
        try:
            # Start connection in background thread
            thread = threading.Thread(
                target=self._connect_wifi_direct_task,
                args=(ssid, password),
                daemon=True
            )
            thread.start()
            
            return {
                'status': 'connecting',
                'message': f'Connecting to {ssid}...',
                'instructions': [
                    'Hotspot will close automatically',
                    'Your device will be disconnected',
                    'System will verify connection after 20 seconds',
                    'Check your device WiFi list for connection status',
                ]
            }
            
        except Exception as e:
            logging.error(f"Error starting WiFi connection: {e}")
            return {
                'status': 'error',
                'message': f'Connection error: {str(e)}'
            }
    
    def disconnect(self) -> Dict:
        """Disconnect from current WiFi connection"""
        try:
            # Get active connection name
            cmd = [self.NMCLI, "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if self.interface_name in line and "802-11-wireless" in line:
                        conn_name = line.split(':')[0]
                        if conn_name and conn_name != "OM1-Hotspot":
                            # Disconnect from this connection
                            disconnect_cmd = [self.NMCLI, "connection", "down", conn_name]
                            subprocess.run(disconnect_cmd, capture_output=True, timeout=10)
                            return {'success': True, 'message': f'Disconnected from {conn_name}'}
            
            return {'success': True, 'message': 'No WiFi connection to disconnect'}
            
        except Exception as e:
            logging.error(f"Error disconnecting WiFi: {e}")
            return {'success': False, 'message': f'Disconnect error: {str(e)}'}
    
    def stop_hotspot(self) -> Dict:
        """Stop the hotspot connection"""
        try:
            result = subprocess.run(
                [self.NMCLI, "connection", "down", "OM1-Hotspot"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {'success': True, 'message': 'Hotspot stopped'}
            else:
                logging.warning(f"Failed to stop hotspot: {result.stderr}")
                return {'success': False, 'message': 'Failed to stop hotspot', 'error': result.stderr}
                
        except Exception as e:
            logging.error(f"Error stopping hotspot: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    def start_hotspot(self) -> Dict:
        """Start the hotspot connection"""
        try:
            result = subprocess.run(
                [self.NMCLI, "connection", "up", "OM1-Hotspot"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                return {'success': True, 'message': 'Hotspot started'}
            else:
                logging.warning(f"Failed to start hotspot: {result.stderr}")
                return {'success': False, 'message': 'Failed to start hotspot', 'error': result.stderr}
                
        except Exception as e:
            logging.error(f"Error starting hotspot: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    def delete_connection(self, ssid: str) -> Dict:
        """Delete a WiFi connection profile"""
        try:
            result = subprocess.run(
                [self.NMCLI, "connection", "delete", ssid],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {'success': True, 'message': f'Connection {ssid} deleted'}
            else:
                return {'success': False, 'message': f'Failed to delete connection', 'error': result.stderr}
                
        except Exception as e:
            logging.error(f"Error deleting connection: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    def _connect_wifi_direct_task(self, ssid: str, password: str):
        """Background task to connect to WiFi"""
        try:
            # Wait 5 seconds to let user see the response
            time.sleep(5)
            
            # Step 1: Stop hotspot
            self.stop_hotspot()
            
            # Wait for hotspot to fully stop and interface to stabilize
            time.sleep(10)
            
            # Step 2: Direct device connect (bypasses connection add)
            cmd = [self.NMCLI, "device", "wifi", "connect", ssid]
            
            if password:
                cmd.extend(["password", password])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logging.error(f"Direct connection failed: {result.stderr}")
                # Connection failed, restart hotspot
                self._handle_connection_failure(ssid)
                return
            
            time.sleep(20)
            
            status = self.get_connection_status()
            if status.get('connected') and status.get('ssid') == ssid:
                logging.info(f"WiFi connection verified: {ssid}")
            else:
                logging.error(f"WiFi connection verification failed for {ssid}")
                self._handle_connection_failure(ssid)
                
        except Exception as e:
            logging.error(f"Direct WiFi connection task error: {e}")
            self._handle_connection_failure(ssid)
    
    def _handle_connection_failure(self, ssid: str):
        """Handle WiFi connection failure"""
        try:
            # Wait a bit to ensure connection attempt is fully failed
            time.sleep(20)
            
            # Try to delete the failed connection
            self.delete_connection(ssid)
            
            # Wait before restarting hotspot
            time.sleep(5)
            
            # Restart hotspot
            result = self.start_hotspot()
            
            if not result.get('success'):
                logging.error("Failed to restart hotspot after connection failure")
                
        except Exception as e:
            logging.error(f"Error handling connection failure: {e}")
