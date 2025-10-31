#!/bin/bash
# OM1 Hotspot Configuration

set -euo pipefail

# Configuration
readonly HOTSPOT_SSID="${HOTSPOT_SSID:-OM1-Setup}"
readonly HOTSPOT_PASSWORD="${HOTSPOT_PASSWORD:-openmind123}"
readonly WIFI_INTERFACE="${WIFI_INTERFACE:-wlP1p1s0}"
readonly CONNECTION_NAME="OM1-Hotspot"

validate_config() {
    if [[ $EUID -ne 0 ]]; then
        echo "ERROR: This script must be run as root (use sudo)"
        exit 1
    fi
    
    if [[ -z "$HOTSPOT_SSID" || ${#HOTSPOT_SSID} -gt 32 ]]; then
        echo "ERROR: SSID must be 1-32 characters"
        exit 1
    fi
    
    if [[ -z "$HOTSPOT_PASSWORD" || ${#HOTSPOT_PASSWORD} -lt 8 || ${#HOTSPOT_PASSWORD} -gt 63 ]]; then
        echo "ERROR: Password must be 8-63 characters"
        exit 1
    fi
    
    if ! nmcli device show "$WIFI_INTERFACE" &>/dev/null; then
        echo "ERROR: WiFi interface '$WIFI_INTERFACE' not found"
        echo "Available interfaces:"
        nmcli device status | grep wifi | awk '{print "  - " $1}' || true
        exit 1
    fi
}

# Remove existing hotspot connection
remove_existing_connection() {
    if nmcli connection show "$CONNECTION_NAME" &>/dev/null; then
        echo "Removing existing hotspot..."
        nmcli connection delete "$CONNECTION_NAME" &>/dev/null || exit 1
    fi
}

# Create hotspot
create_hotspot_connection() {
    echo "Creating 5GHz hotspot..."
    
    nmcli connection add \
        type wifi \
        ifname "$WIFI_INTERFACE" \
        con-name "$CONNECTION_NAME" \
        autoconnect no \
        ssid "$HOTSPOT_SSID" \
        mode ap \
        ipv4.method shared \
        ipv4.addresses 10.42.0.1/24 \
        wifi-sec.key-mgmt wpa-psk \
        wifi-sec.psk "$HOTSPOT_PASSWORD" \
        wifi.band a \
        wifi.channel 36 &>/dev/null || exit 1
    
    echo "5GHz hotspot configured (Bluetooth compatible)"
}

# Display summary
display_summary() {
    echo ""
    echo "=== Hotspot Configuration Complete ==="
    echo ""
    echo "  SSID:       $HOTSPOT_SSID"
    echo "  Password:   $HOTSPOT_PASSWORD"
    echo "  Frequency:  5GHz (Channel 36)"
    echo "  Gateway:    10.42.0.1"
    echo "  Bluetooth:  Compatible"
    echo ""
    echo "Control:"
    echo "  Start:  sudo nmcli connection up $CONNECTION_NAME"
    echo "  Stop:   sudo nmcli connection down $CONNECTION_NAME"
    echo ""
    echo "Access:  http://om1-setup or http://10.42.0.1"
    echo ""
}

# Main function
main() {
    echo "=== OM1 5GHz Hotspot Setup ==="
    echo ""
    
    validate_config
    remove_existing_connection
    create_hotspot_connection
    display_summary
    
    echo "✓ Setup complete!"
}

main "$@"
