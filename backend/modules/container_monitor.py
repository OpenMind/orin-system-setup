import subprocess
import json
import logging
import requests
from typing import Dict, Optional


class ContainerMonitor:
    """Monitors Docker containers """
    
    def __init__(self, stream_monitor=None):
        """Initialize container monitor with container definitions."""
        self.stream_monitor = stream_monitor
        self.containers = {
            'video_processor': {
                'name': 'om1_video_processor',
                'display_name': 'Video Processor',
                'description': 'Video/Audio processing and face recognition'
            },
            'ros2_sensor': {
                'name': 'om1_sensor',
                'display_name': 'ROS2 Sensor',
                'description': 'Robot sensors and camera streams'
            },
            'orchestrator': {
                'name': 'orchestrator',
                'display_name': 'Orchestrator',
                'description': 'Navigation, SLAM and charging controller',
                'api_endpoint': 'http://localhost:5000/status'
            }
        }
    
    def find_container_name(self, name_pattern: str) -> Optional[str]:
        """
        Find the container using docker ps.
            
        Returns:
            Actual container name if found, None otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={name_pattern}", 
                 "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # if not found, container status might be stopped, try ps -a
            if result.returncode != 0 or not result.stdout.strip():
                result = subprocess.run(
                    ["docker", "ps", "-a", "--filter", f"name={name_pattern}", 
                     "--format", "{{.Names}}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            if result.returncode != 0 or not result.stdout.strip():
                return None
            
            # Get all names
            container_names = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
            
            if not container_names:
                return None
            
            for name in container_names:
                if name == name_pattern:
                    return name
            
            matching = [n for n in container_names if name_pattern in n]
            if matching:
                return min(matching, key=len)
            
            return None
            
        except Exception as e:
            logging.error(f"Error finding container {name_pattern}: {str(e)}")
            return None
    
    def get_container_status(self, container_name: str) -> Dict:
        """
        Get the status of the container 
        
        """
        try:
            result = subprocess.run(
                ["docker", "inspect", container_name, 
                 "--format", "{{.State.Status}}|{{.State.Running}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return {
                    'running': False,
                    'status': 'not_found'
                }
            
            parts = result.stdout.strip().split('|')
            if len(parts) < 2:
                return {
                    'running': False,
                    'status': 'error',
                    'error': 'Invalid docker inspect output'
                }
            
            status, running = parts[0], parts[1]
            
            return {
                'running': running.lower() == 'true',
                'status': status
            }
            
        except Exception as e:
            return {
                'running': False,
                'status': 'error',
                'error': str(e)
            }
    
    def get_container_uptime(self, container_name: str) -> Optional[str]:
        try:
            result = subprocess.run(
                ["docker", "inspect", container_name,
                 "--format", "{{.State.StartedAt}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            return None
            
        except Exception:
            return None
    
    def check_http_health(self, url: str) -> Dict:
        """Check HTTP endpoint."""
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                try:
                    data = response.json()
                    return {
                        'healthy': True,
                        'status_code': 200,
                        'data': data
                    }
                except:
                    return {
                        'healthy': True,
                        'status_code': 200
                    }
            else:
                return {
                    'healthy': False,
                    'status_code': response.status_code
                }
        except requests.exceptions.ConnectionError:
            return {
                'healthy': False,
                'error': 'Connection refused'
            }
        except requests.exceptions.Timeout:
            return {
                'healthy': False,
                'error': 'Timeout'
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def get_ros2_camera_streams(self) -> Dict:
        """Get local RTSP check."""
        streams = {}
        
        for camera_name in ['front_camera', 'down_camera']:
            stream_info = {
                'name': f'{camera_name.replace("_", " ").title()}',
                'type': 'video',
                'rtsp_path': f'rtsp://localhost:8554/{camera_name}',
                'source': 'ros2',
                'status': 'unknown',
                'streaming': False
            }
            
            if self.stream_monitor:
                rtsp_status = self.stream_monitor.check_local_rtsp_stream(camera_name)
                stream_info['streaming'] = rtsp_status.get('streaming', False)
                stream_info['status'] = 'running' if rtsp_status.get('streaming') else 'stopped'
                if 'error' in rtsp_status:
                    stream_info['error'] = rtsp_status['error']
            
            streams[camera_name] = stream_info
        
        return streams
    
    def get_orchestrator_services(self) -> Optional[Dict]:
        """Get orchestrator local API."""
        health = self.check_http_health('http://localhost:5000/status')
        
        if health.get('healthy') and 'data' in health:
            try:
                import json
                status_data = json.loads(health['data'].get('message', '{}'))
                return {
                    'slam': status_data.get('slam_status', 'unknown'),
                    'nav2': status_data.get('nav2_status', 'unknown'),
                    'base_control': status_data.get('base_control_status', 'unknown'),
                    'charging_dock': status_data.get('charging_dock_status', 'unknown'),
                    'is_charging': status_data.get('is_charging', False),
                    'battery_soc': status_data.get('battery_soc', 0.0)
                }
            except:
                return None
        
        return None
    
    def get_all_containers_status(self) -> Dict:
        """ Get status of all monitored containers. """
        result = {
            'video_processor': {
                'display_name': 'Video Processor',
                'container_name': 'om1_video_processor',
                'container_status': None,
                'local_streams': [],
                'cloud_streams': []
            },
            'ros2_sensor': {
                'display_name': 'ROS2 Sensor',
                'container_name': 'om1_sensor',
                'container_status': None,
                'local_streams': []
            },
            'orchestrator': {
                'display_name': 'Orchestrator',
                'container_name': 'orchestrator',
                'container_status': None,
                'services': {}
            }
        }
        
        if self.stream_monitor:
            container_running_status = self.stream_monitor.get_container_status()
            result['video_processor']['container_status'] = {
                'running': container_running_status.get('running', False),
                'status': 'running' if container_running_status.get('running') else 'stopped'
            }
            all_streams = self.stream_monitor.get_all_streams_status()
        else:
            result['video_processor']['container_status'] = self.get_container_status('om1_video_processor')
            all_streams = {}
        
        if all_streams:
            
            if 'audio' in all_streams:
                result['video_processor']['local_streams'].append({
                    'name': 'Audio (Mic Local)',
                    'status': all_streams['audio'].get('status', 'unknown'),
                    'type': 'audio'
                })
            
            if 'top_camera' in all_streams:
                result['video_processor']['local_streams'].append({
                    'name': 'Top Camera Local',
                    'status': all_streams['top_camera'].get('status', 'unknown'),
                    'type': 'video'
                })
            
            if 'audio_cloud' in all_streams:
                result['video_processor']['cloud_streams'].append({
                    'name': 'Audio Cloud',
                    'status': all_streams['audio_cloud'].get('status', 'unknown'),
                    'type': 'audio'
                })
            
            if 'top_camera_cloud' in all_streams:
                result['video_processor']['cloud_streams'].append({
                    'name': 'Top Camera Cloud',
                    'status': all_streams['top_camera_cloud'].get('status', 'unknown'),
                    'type': 'video'
                })
        
        # ROS2 Sensor
        result['ros2_sensor']['container_status'] = self.get_container_status('om1_sensor')
        ros2_streams = self.get_ros2_camera_streams()
        
        for stream_key, stream_data in ros2_streams.items():
            result['ros2_sensor']['local_streams'].append({
                'name': stream_data['name'],
                'status': stream_data.get('status', 'unknown'),
                'type': 'video',
                'streaming': stream_data.get('streaming', False)
            })
            
            result['video_processor']['cloud_streams'].append({
                'name': f"{stream_data['name']} Cloud",
                'status': stream_data.get('status', 'unknown'),
                'type': 'video',
                'source': 'ros2'
            })
        
        # Orchestrator
        result['orchestrator']['container_status'] = self.get_container_status('orchestrator')
        orchestrator_services = self.get_orchestrator_services()
        if orchestrator_services:
            result['orchestrator']['services'] = orchestrator_services
        
        return result
