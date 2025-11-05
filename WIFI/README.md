# OM1 WiFi setup Portal

WiFi configuration portal with 5GHz hotspot and system monitoring dashboard for OM1 robot.

## Quick Start

### Installation

Setup the hostname first:

```bash
hostnamectl set-hostname "$NETWORK_NAME"
```

After updating the hostname, reboot the system:

```bash
sudo reboot
```

You also might need to re-install chromium to reflect the hostname change:

```bash
sudo apt uninstall -y chromium-browser
sudo apt install -y chromium-browser
```

Add the new hostname to your `/etc/hosts` file:

```bash
127.0.1.1   $NETWORK_NAME
```

Run the install script as root:

```bash
cd orin-system-setup/WIFI
sudo bash ./scripts/install.sh -n $NETWORK_NAME
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
