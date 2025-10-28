import subprocess
import re
from typing import Dict, List, Optional


class StreamMonitor:
    
    def __init__(self, container_name: str = "om1_video_processor"):
        self.container_name = container_name
    
    def get_supervisord_status(self) -> Dict:
        """
        Get status of all supervisord processes in the container
        
        Returns:
            Dict with process statuses
        """
        try:
            result = subprocess.run(
                ["docker", "exec", self.container_name, "supervisorctl", "status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0 and "RUNNING" not in result.stdout and "FATAL" not in result.stdout:
                return {'error': 'Failed to get supervisor status', 'details': result.stderr}
            
            processes = {}
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                
                if 'UserWarning' in line or 'pkg_resources' in line or line.startswith('/usr/'):
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    status = parts[1]
                    
                    processes[name] = {
                        'status': status,
                        'running': status.upper() == 'RUNNING',
                        'pid': parts[2] if len(parts) > 2 and parts[2].isdigit() else None
                    }
            
            if not processes:
                return {'error': 'No supervisor processes found', 'details': result.stdout}
            
            return processes
            
        except Exception as e:
            return {'error': str(e)}
    
    def check_ffmpeg_stream(self, stream_name: str) -> Dict:
        """
        Check if specific ffmpeg stream process is running
        
        Returns:
            Dict with stream status
        """
        try:
            result = subprocess.run(
                ["docker", "exec", self.container_name, "ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return {'running': False, 'error': 'Failed to check process'}
            
            for line in result.stdout.split('\n'):
                if 'ffmpeg' in line.lower() and stream_name in line.lower():
                    return {
                        'running': True,
                        'process_found': True
                    }
            
            return {
                'running': False,
                'process_found': False
            }
            
        except Exception as e:
            return {'running': False, 'error': str(e)}
    
    def check_camera_device(self, device_path: str = "/dev/video0") -> Dict:
        """
        Check if camera device is accessible in container
        
        Returns:
            Dict with device status
        """
        try:
            result = subprocess.run(
                ["docker", "exec", self.container_name, "test", "-c", device_path],
                capture_output=True,
                timeout=5
            )
            
            device_exists = result.returncode == 0
            
            if not device_exists:
                return {
                    'accessible': False,
                    'device': device_path,
                    'error': 'Device not found'
                }
            
            info_result = subprocess.run(
                ["docker", "exec", self.container_name, "v4l2-ctl", "--device", device_path, "--info"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            return {
                'accessible': device_exists,
                'device': device_path,
                'info_available': info_result.returncode == 0
            }
            
        except Exception as e:
            return {
                'accessible': False,
                'device': device_path,
                'error': str(e)
            }
    
    def check_audio_device(self) -> Dict:
        """
        Check if audio device (PulseAudio) is accessible
        
        Returns:
            Dict with audio status
        """
        try:
            result = subprocess.run(
                ["docker", "exec", self.container_name, "pactl", "info"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return {
                    'accessible': True,
                    'pulseaudio_connected': True
                }
            else:
                return {
                    'accessible': False,
                    'pulseaudio_connected': False,
                    'error': result.stderr
                }
                
        except Exception as e:
            return {
                'accessible': False,
                'error': str(e)
            }
    
    def check_local_rtsp_stream(self, stream_path: str) -> Dict:
        """
        Check if local RTSP stream is available and streaming
        
        Returns:
            Dict with stream availability status
        """
        try:
            result = subprocess.run(
                ["docker", "exec", self.container_name, 
                 "ffprobe", 
                 "-v", "error",
                 "-show_entries", "stream=codec_type",
                 "-of", "default=noprint_wrappers=1:nokey=1",
                 f"rtsp://localhost:8554/{stream_path}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return {
                    'available': True,
                    'streaming': True,
                    'codec_info': result.stdout.strip()
                }
            else:
                return {
                    'available': False,
                    'streaming': False,
                    'error': result.stderr if result.stderr else 'No stream data'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'available': False,
                'streaming': False,
                'error': 'Stream check timeout'
            }
        except Exception as e:
            return {
                'available': False,
                'streaming': False,
                'error': str(e)
            }
    
    def get_all_streams_status(self) -> Dict:
        """
        Get comprehensive status of all streams
        
        Returns:
            Dict with status of audio and top_camera (actual configured streams)
        """
        supervisor_status = self.get_supervisord_status()
        
        streams = {
            'audio': {
                'name': 'Local audio status',
                'type': 'audio',
                'supervisor_program': 'mic_local',
                'rtsp_path': 'audio'
            },
            'top_camera': {
                'name': 'Local front camera status',
                'type': 'video',
                'supervisor_program': 'top_camera_local',
                'device': '/dev/video0',
                'rtsp_path': 'top_camera'
            },
            'audio_cloud': {
                'name': 'Cloud audio status',
                'type': 'audio',
                'supervisor_program': 'mic_cloud',
                'cloud_stream': True
            },
            'top_camera_cloud': {
                'name': 'Cloud camera status',
                'type': 'video',
                'supervisor_program': 'top_camera_cloud',
                'cloud_stream': True
            }
        }
        
        result = {}
        
        for stream_id, stream_info in streams.items():
            supervisor_prog = stream_info['supervisor_program']
            
            if 'error' in supervisor_status:
                result[stream_id] = {
                    'status': 'error',
                    'name': stream_info['name'],
                    'type': stream_info['type'],
                    'error': 'Cannot connect to container'
                }
                continue
            
            if supervisor_prog in supervisor_status:
                prog_status = supervisor_status[supervisor_prog]
                
                base_status = {
                    'status': 'running' if prog_status['running'] else 'stopped',
                    'name': stream_info['name'],
                    'type': stream_info['type'],
                    'pid': prog_status.get('pid')
                }
                
                if stream_info.get('cloud_stream'):
                    base_status['cloud_stream'] = True
                else:
                    if stream_info['type'] == 'video' and 'device' in stream_info:
                        device_status = self.check_camera_device(stream_info['device'])
                        base_status['device'] = stream_info['device']
                        base_status['device_accessible'] = device_status.get('accessible', False)
                    
                    if stream_info['type'] == 'audio':
                        audio_status = self.check_audio_device()
                        base_status['device_accessible'] = audio_status.get('accessible', False)
                    
                    if prog_status['running'] and 'rtsp_path' in stream_info:
                        rtsp_status = self.check_local_rtsp_stream(stream_info['rtsp_path'])
                        base_status['rtsp_streaming'] = rtsp_status.get('streaming', False)
                        if not rtsp_status.get('streaming'):
                            # If process running but stream not available, mark as error
                            base_status['status'] = 'running_no_stream'
                            base_status['stream_error'] = rtsp_status.get('error', 'Stream not available')
                
                result[stream_id] = base_status
            else:
                result[stream_id] = {
                    'status': 'not_configured',
                    'name': stream_info['name'],
                    'type': stream_info['type'],
                    'message': 'Stream not configured in supervisor'
                }
        
        return result
    
    def get_container_status(self) -> Dict:
        """
        Check if the video processor container is running
        
        Returns:
            Dict with container status
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self.container_name}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return {
                    'running': True,
                    'status': result.stdout.strip()
                }
            else:
                return {
                    'running': False,
                    'status': 'Container not running'
                }
                
        except Exception as e:
            return {
                'running': False,
                'error': str(e)
            }
