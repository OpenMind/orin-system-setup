from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from modules import WiFiManager, StreamMonitor

static_folder = os.path.join(os.path.dirname(__file__), 'static')
app = Flask(__name__, static_folder=static_folder, static_url_path='')
CORS(app)  

wifi_manager = WiFiManager()
stream_monitor = StreamMonitor()


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


@app.route('/api/wifi/networks', methods=['GET'])
def get_wifi_networks():
    try:
        networks = wifi_manager.scan_networks()
        return jsonify({
            'success': True,
            'data': networks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/wifi/connect', methods=['POST'])
def connect_wifi():
    try:
        data = request.get_json()
        ssid = data.get('ssid')
        password = data.get('password', '')
        
        if not ssid:
            return jsonify({
                'success': False,
                'error': 'SSID is required'
            }), 400
        
        result = wifi_manager.connect(ssid, password)
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
    print(f"Starting Orin System Monitor on port {port}...")
    print(f"Access the dashboard at http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
