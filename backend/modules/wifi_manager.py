import subprocess
import re
from typing import List, Dict, Optional


class WiFiManager:    
    NMCLI = "/usr/bin/nmcli"  # Fixed path to avoid version conflicts
    
    def __init__(self, interface_name: str = "wlP1p1s0"):
        self.interface_name = interface_name
    
    def get_connection_status(self) -> Dict:
        """
        Get current WiFi connection status
        
        Returns:
            Dict with connection details
        """
        try:
            result = subprocess.run(
                [self.NMCLI, "-t", "-f", "DEVICE,STATE,CONNECTION", "device", "status"],
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
                            'interface': device,
                            'state': state
                        }
            
            return {
                'connected': False,
                'ssid': None,
                'interface': self.interface_name,
                'state': 'unknown'
            }
            
        except Exception as e:
            return {
                'connected': False,
                'ssid': None,
                'interface': self.interface_name,
                'error': str(e)
            }
    
    def scan_networks(self) -> List[Dict]:
        """
        Scan for available WiFi networks
        
        Returns:
            List of network dictionaries
        """
        networks = []
        
        try:
            # Request rescan
            subprocess.run(
                [self.NMCLI, "device", "wifi", "rescan"],
                capture_output=True,
                timeout=10
            )
            
            # Get network list
            result = subprocess.run(
                [self.NMCLI, "-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE", "device", "wifi", "list", "ifname", self.interface_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return networks
            
            seen_ssids = set()
            
            for line in result.stdout.strip().split('\n'):
                parts = line.split(':')
                if len(parts) >= 4:
                    ssid = parts[0].strip()
                    signal = parts[1].strip()
                    security = parts[2].strip()
                    in_use = parts[3].strip()
                    
                    # Skip empty SSIDs and duplicates
                    if not ssid or ssid in seen_ssids:
                        continue
                    
                    seen_ssids.add(ssid)
                    
                    try:
                        signal_strength = int(signal) if signal.isdigit() else 0
                    except:
                        signal_strength = 0
                    
                    networks.append({
                        'ssid': ssid,
                        'signal': signal_strength,
                        'security': security if security else 'Open',
                        'connected': in_use == '*'
                    })
            
            # Sort by signal strength
            networks.sort(key=lambda x: x['signal'], reverse=True)
            
        except Exception as e:
            print(f"WiFi scan error: {e}")
        
        return networks
    
    def connect(self, ssid: str, password: str = '') -> Dict:
        """
        Connect to a WiFi network
        
        Args:
            ssid: Network SSID
            password: Network password (optional for open networks)
        
        Returns:
            Dict with status and message
        """
        try:
            cmd = [self.NMCLI, "device", "wifi", "connect", ssid, "ifname", self.interface_name]
            if password:
                cmd.extend(["password", password])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': f'Connected to {ssid}',
                    'ssid': ssid
                }
            else:
                return {
                    'success': False,
                    'message': f'Failed to connect to {ssid}',
                    'error': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': f'Connection timeout for {ssid}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection error: {str(e)}'
            }
    
    def disconnect(self) -> Dict:
        """
        Disconnect from current WiFi network
        
        Returns:
            Dict with status and message
        """
        try:
            result = subprocess.run(
                [self.NMCLI, "device", "disconnect", self.interface_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': f'Disconnected from WiFi'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to disconnect',
                    'error': result.stderr
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Disconnect error: {str(e)}'
            }
