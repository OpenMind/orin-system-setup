#!/bin/bash
# OM1 Hotspot Monitor 

set -euo pipefail

# Configuration
readonly CONNECTION_NAME="OM1-Hotspot"
readonly WIFI_INTERFACE="${WIFI_INTERFACE:-wlP1p1s0}"
readonly LOG_FILE="/var/log/om1-hotspot.log"
readonly MAX_RETRIES=3
readonly RETRY_DELAY=5

# Logging functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

# Check if WiFi connected 
check_internet_connectivity() {
    local wifi_device_state
    wifi_device_state=$(nmcli -t -f DEVICE,STATE device show | grep "${WIFI_INTERFACE}:connected" || true)
    
    if [[ -n "$wifi_device_state" ]]; then
        local active_connection
        active_connection=$(nmcli -t -f NAME,TYPE,DEVICE connection show --active | \
            grep "${WIFI_INTERFACE}" | grep "802-11-wireless" | \
            grep -v "$CONNECTION_NAME" | cut -d: -f1 || true)
        
        if [[ -n "$active_connection" ]]; then
            log "Connected to: $active_connection"
            return 0
        fi
    fi
    
    return 1
}

# Check if hotspot is currently active
is_hotspot_active() {
    nmcli connection show --active | grep -q "$CONNECTION_NAME" || return 1
}

# Stop hotspot if active
stop_hotspot() {
    if is_hotspot_active; then
        log "Stopping hotspot..."
        nmcli connection down "$CONNECTION_NAME" &>/dev/null || true
        sleep 2
    fi
}

start_hotspot() {
    local retry=0
    
    ip link set "$WIFI_INTERFACE" up 2>/dev/null || true
    sleep 1
    
    while (( retry < MAX_RETRIES )); do
        log "Starting hotspot (attempt $((retry+1))/$MAX_RETRIES)..."
        
        if nmcli connection up "$CONNECTION_NAME" &>/dev/null; then
            sleep 3
            
            if is_hotspot_active; then
                local ssid
                ssid=$(nmcli -t -f 802-11-wireless.ssid connection show "$CONNECTION_NAME" | cut -d: -f2)
                
                log "Hotspot started: ${ssid:-Unknown} (10.42.0.1)"
                return 0
            fi
        fi
        
        ((retry++))
        if (( retry < MAX_RETRIES )); then
            sleep "$RETRY_DELAY"
        fi
    done
    
    log_error "Failed to start hotspot after $MAX_RETRIES attempts"
    return 1
}

# Validate prerequisites
validate_prerequisites() {
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
    
    # Check if hotspot connection exists
    if ! nmcli connection show "$CONNECTION_NAME" &>/dev/null; then
        log_error "Hotspot connection '$CONNECTION_NAME' not found"
        log_error "Please run: sudo /app/scripts/hotspot-configure.sh"
        exit 1
    fi
    
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    chmod 644 "$LOG_FILE"
}

main() {
    log "=== OM1 Hotspot Monitor Started ==="
    
    # Validate prerequisites
    validate_prerequisites
    
    # Wait 10 seconds before checking connectivity
    sleep 10
    
    # Check internet connectivity
    if check_internet_connectivity; then
        log "Internet available, disabling hotspot"
        stop_hotspot
        exit 0
    fi
    
    # No internet, start hotspot
    log "No internet, starting hotspot..."
    
    # Stop any existing hotspot first
    stop_hotspot
    
    # Start hotspot
    if start_hotspot; then
        log "=== Hotspot active ==="
        exit 0
    else
        log_error "=== Failed to start hotspot ==="
        exit 1
    fi
}

main "$@"
