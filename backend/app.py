from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from modules import WiFiManager, StreamMonitor, ContainerMonitor

static_folder = os.path.join(os.path.dirname(__file__), 'static')
app = Flask(__name__, static_folder=static_folder, static_url_path='')
CORS(app)  

wifi_manager = WiFiManager()
stream_monitor = StreamMonitor()
container_monitor = ContainerMonitor(stream_monitor=stream_monitor)


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'service': 'orin-system-monitor'
    })


@app.route('/api/wifi/status', methods=['GET'])
def get_wifi_status():
    try:
        status = wifi_manager.get_connection_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/wifi/connect', methods=['POST'])
def connect_wifi():
    """
    Connect to WiFi with async hotspot management
    
    POST body:
    {
        "ssid": "WiFi-Name",
        "password": "wifi-password"
    }
    """
    try:
        data = request.get_json()
        ssid = data.get('ssid')
        password = data.get('password', '')
        
        # Validate input
        if not ssid:
            return jsonify({
                'success': False,
                'error': 'SSID is required'
            }), 400
        
        if not ssid.strip():
            return jsonify({
                'success': False,
                'error': 'SSID cannot be empty'
            }), 400
        
        # Use async connection with hotspot management
        result = wifi_manager.connect_wifi_async(ssid.strip(), password)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/wifi/disconnect', methods=['POST'])
def disconnect_wifi():
    try:
        result = wifi_manager.disconnect()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/streams/status', methods=['GET'])
def get_streams_status():
    try:
        container_status = stream_monitor.get_container_status()
        
        if not container_status.get('running'):
            return jsonify({
                'success': True,
                'data': {
                    'container_running': False,
                    'streams': {
                        'audio': {'status': 'unavailable', 'name': 'Local audio status', 'type': 'audio'},
                        'top_camera': {'status': 'unavailable', 'name': 'Local front camera status', 'type': 'video'}
                    }
                }
            })
        
        streams = stream_monitor.get_all_streams_status()
        return jsonify({
            'success': True,
            'data': {
                'container_running': True,
                'streams': streams
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/streams/container/status', methods=['GET'])
def get_container_status():
    try:
        status = stream_monitor.get_container_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/containers/status', methods=['GET'])
def get_containers_status():
    try:
        containers = container_monitor.get_all_containers_status()
        return jsonify({
            'success': True,
            'data': containers
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path.startswith('api/'):
        return {'error': 'API endpoint not found'}, 404
    
    if path != "" and os.path.exists(os.path.join(static_folder, path)):
        return send_from_directory(static_folder, path)
    else:
        return send_from_directory(static_folder, 'index.html')


if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)
