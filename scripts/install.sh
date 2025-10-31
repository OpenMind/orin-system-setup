#!/bin/bash
# OM1 WiFi Portal Installation Script

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly SERVICE_NAME="om1-hotspot"
readonly SCRIPT_PREFIX="om1"

log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
}

log_success() {
    echo "[SUCCESS] $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_requirements() {
    log_info "Checking system requirements..."
    
    local required_commands=("nmcli" "systemctl" "ip")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Missing required command: $cmd"
            exit 1
        fi
    done
    
    if ! systemctl is-active --quiet NetworkManager; then
        log_error "NetworkManager is not running"
        exit 1
    fi
    
    log_success "Requirements check passed"
}

# Install scripts to system location
install_scripts() {
    log_info "Installing scripts..."
    
    local scripts=(
        "hotspot-configure.sh:${SCRIPT_PREFIX}-configure"
        "hotspot-monitor.sh:${SCRIPT_PREFIX}-monitor"
    )
    
    for script_mapping in "${scripts[@]}"; do
        local source_script="${script_mapping%:*}"
        local target_script="${script_mapping#*:}"
        
        cp "$SCRIPT_DIR/$source_script" "/usr/local/bin/${target_script}.sh"
        chmod +x "/usr/local/bin/${target_script}.sh"
    done
    
    log_success "Scripts installed"
}

configure_hotspot() {
    log_info "Configuring hotspot..."
    
    if /usr/local/bin/${SCRIPT_PREFIX}-configure.sh; then
        log_success "Hotspot configured"
    else
        log_error "Failed to configure hotspot"
        exit 1
    fi
}

install_service() {
    log_info "Installing systemd service..."
    
    local service_file="$PROJECT_ROOT/systemd/${SERVICE_NAME}.service"
    
    if [[ ! -f "$service_file" ]]; then
        log_error "Service file not found: $service_file"
        exit 1
    fi
    
    cp "$service_file" "/etc/systemd/system/"
    chmod 644 "/etc/systemd/system/${SERVICE_NAME}.service"
    log_success "Service installed"
}

configure_dns() {
    log_info "Configuring DNS..."
    
    local dns_config="$PROJECT_ROOT/config/dnsmasq-om1.conf"
    local dns_dir="/etc/NetworkManager/dnsmasq-shared.d"
    
    if [[ ! -f "$dns_config" ]]; then
        log_info "DNS config not found, skipping..."
        return 0
    fi
    
    mkdir -p "$dns_dir"
    cp "$dns_config" "$dns_dir/"
    chmod 644 "$dns_dir/dnsmasq-om1.conf"
    log_success "DNS configured"
}

# Setup logging
setup_logging() {
    log_info "Setting up logging..."
    
    local log_file="/var/log/om1-hotspot.log"
    
    touch "$log_file"
    chmod 644 "$log_file"
    log_success "Logging setup complete"
}

# Enable systemd service
enable_service() {
    log_info "Configuring service..."
    
    systemctl daemon-reload
    
    systemctl enable "${SERVICE_NAME}.service"
    log_success "Service enabled"
}

# Display summary
display_summary() {
    echo ""
    echo "=== Installation Complete ==="
    echo ""
    echo "Service Management:"
    echo "  Start:   sudo systemctl start ${SERVICE_NAME}.service"
    echo "  Stop:    sudo systemctl stop ${SERVICE_NAME}.service"
    echo "  Status:  sudo systemctl status ${SERVICE_NAME}.service"
    echo "  Logs:    sudo journalctl -u ${SERVICE_NAME}.service -f"
    echo ""
    echo "Hotspot Control:"
    echo "  Start:   sudo nmcli connection up OM1-Hotspot"
    echo "  Stop:    sudo nmcli connection down OM1-Hotspot"
    echo ""
    echo "Client Connection:"
    echo "  SSID:    OM1-Setup"
    echo "  Password: openmind123"
    echo "  Gateway: 10.42.0.1"
    echo ""
    echo "Dashboard:"
    echo "  http://om1-setup"
    echo ""
    echo "Next Steps:"
    echo "1. Start service: sudo systemctl start ${SERVICE_NAME}.service"
    echo "2. Check status:  sudo systemctl status ${SERVICE_NAME}.service"
    echo "3. Connect to 'OM1-Setup' WiFi"
    echo "4. Access http://om1-setup"
    echo ""
}

main() {
    echo "=== OM1 WiFi Portal Installation ==="
    echo ""
    
    # Run installation steps
    check_root
    check_requirements
    install_scripts
    configure_hotspot
    install_service
    configure_dns
    setup_logging
    enable_service
    
    # Display summary
    display_summary
    
    log_success "Installation completed!"
}

main "$@"
