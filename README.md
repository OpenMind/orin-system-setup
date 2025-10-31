# OM1 WiFi Portal

WiFi configuration portal with 5GHz hotspot and system monitoring dashboard for OM1 robot.

## Quick Start

### Installation

Run the install script as root:

```bash
cd om1-wifi-portal
sudo bash ./scripts/install.sh
```

The system will automatically start the hotspot if no internet connection is detected.

## Project Structure

### Backend

Python Flask application providing REST APIs for:

- **WiFi Management** - Connect to WiFi networks, manage connections
- **Container Monitoring** - Track Docker container status and health
- **Stream Monitoring** - Monitor video/audio streams from containers
- **System Status** - Real-time system health checks

### Frontend

React-based web dashboard accessible via:
- http://om1-setup

or

- http://10.42.0.1

Features:
- WiFi connection interface
- Container status display
- System monitoring dashboard

### Start Hotspot

```bash
sudo nmcli connection up OM1-Hotspot
```

### Stop Hotspot

```bash
sudo nmcli connection down OM1-Hotspot
```

### Connect to WiFi

Access the web portal at http://om1-setup or http://10.42.0.1 and use the WiFi connection interface.

### Service Management

```bash
# Check service status
sudo systemctl status om1-hotspot.service

# Restart service
sudo systemctl restart om1-hotspot.service
```

### Hotspot Not Starting

Check WiFi interface name:
```bash
nmcli device status | grep wifi
```

Update interface in environment if needed:
```bash
export WIFI_INTERFACE=your_interface_name
sudo ./scripts/install.sh
```

### Cannot Access Dashboard

Verify hotspot is running:
```bash
nmcli connection show --active | grep OM1-Hotspot
```

Check service status:
```bash
sudo systemctl status om1-hotspot.service
```

### 5GHz Not Working

Some devices may not support 5GHz. Verify with:
```bash
iw list | grep "Frequencies"
```

## Development

### Build Docker Image

```bash
docker-compose build
```

### Run Container

```bash
docker-compose up -d
```

### View Container Logs

```bash
docker-compose logs -f orin-monitor
```

## API Endpoints

- GET /api/health - Service health check
- GET /api/wifi/status - WiFi connection status
- POST /api/wifi/connect - Connect to WiFi network
- POST /api/wifi/disconnect - Disconnect from WiFi
- GET /api/containers/status - Docker container status
