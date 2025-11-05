#!/bin/bash
# OM1 WiFi Portal Installation Script

if [ -z "$BASH_VERSION" ]; then
    echo "This script requires bash. Please run with: bash $0 $*"
    exit 1
fi

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly SERVICE_NAME="om1-hotspot"
readonly SCRIPT_PREFIX="om1"

NETWORK_NAME=""

usage() {
    echo "Usage: $0 -n|--network-name NAME [OPTIONS]"
    echo ""
    echo "Required:"
    echo "  -n, --network-name NAME   Set the local network name (required)"
    echo ""
    echo "Options:"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -n mydevice          # Use custom name: mydevice"
    echo "  $0 --network-name robot  # Use custom name: robot"
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--network-name)
                NETWORK_NAME="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    if [[ -z "$NETWORK_NAME" ]]; then
        log_error "Network name is required. Use -n or --network-name to specify it."
        usage
        exit 1
    fi

    if [[ ! "$NETWORK_NAME" =~ ^[a-zA-Z0-9-]+$ ]]; then
        log_error "Network name must contain only letters, numbers, and hyphens"
        exit 1
    fi

    if [[ "$NETWORK_NAME" =~ ^- ]] || [[ "$NETWORK_NAME" =~ -$ ]]; then
        log_error "Network name cannot start or end with a hyphen"
        exit 1
    fi
}

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

install_avahi() {
    log_info "Installing and configuring Avahi (mDNS)..."

    if command -v apt-get &> /dev/null; then
        if ! dpkg -l | grep -q avahi-daemon; then
            log_info "Installing avahi-daemon..."
            apt-get update
            apt-get install -y avahi-daemon avahi-utils
        fi
    elif command -v dnf &> /dev/null; then
        if ! rpm -qa | grep -q avahi; then
            log_info "Installing avahi..."
            dnf install -y avahi avahi-tools
        fi
    elif command -v yum &> /dev/null; then
        if ! rpm -qa | grep -q avahi; then
            log_info "Installing avahi..."
            yum install -y avahi avahi-tools
        fi
    else
        log_error "Unsupported package manager. Please install avahi-daemon manually."
        exit 1
    fi

    create_avahi_service

    systemctl enable avahi-daemon
    systemctl start avahi-daemon

    log_success "Avahi installed and configured"
}

create_avahi_service() {
    log_info "Creating Avahi service configuration..."

    local avahi_service_dir="/etc/avahi/services"
    local service_file="${avahi_service_dir}/${NETWORK_NAME}.service"

    mkdir -p "$avahi_service_dir"

    cat > "$service_file" << EOF
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
    <name replace-wildcards="yes">${NETWORK_NAME}</name>
    <service>
        <type>_http._tcp</type>
        <port>80</port>
        <txt-record>path=/</txt-record>
    </service>
</service-group>
EOF

    chmod 644 "$service_file"
    log_success "Avahi service created: ${NETWORK_NAME}.local"
}

install_scripts() {
    log_info "Installing scripts..."

    local scripts=(
        "hotspot-configure.sh:${SCRIPT_PREFIX}-configure"
        "hotspot-monitor.sh:${SCRIPT_PREFIX}-monitor"
    )

    for script_mapping in "${scripts[@]}"; do
        local source_script="${script_mapping%:*}"
        local target_script="${script_mapping#*:}"

        cat > "/usr/local/bin/${target_script}.sh" << EOF
#!/bin/bash
export NETWORK_NAME="$NETWORK_NAME"
exec "$SCRIPT_DIR/$source_script" "\$@"
EOF
        chmod +x "/usr/local/bin/${target_script}.sh"
    done

    log_success "Scripts installed with network name: $NETWORK_NAME"
}

configure_hotspot() {
    log_info "Configuring hotspot..."

    export NETWORK_NAME="$NETWORK_NAME"

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
    local target_service="/etc/systemd/system/${SERVICE_NAME}.service"

    if [[ ! -f "$service_file" ]]; then
        log_error "Service file not found: $service_file"
        exit 1
    fi

    cp "$service_file" "$target_service"

    sed -i "s/Environment=\"NETWORK_NAME=om1-setup\"/Environment=\"NETWORK_NAME=${NETWORK_NAME}\"/" "$target_service"

    chmod 644 "$target_service"
    log_success "Service installed with network name: $NETWORK_NAME"
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
    echo "Network Configuration:"
    echo "  Local Name:  ${NETWORK_NAME}.local"
    echo "  mDNS:        Enabled (Avahi)"
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
    echo "Dashboard Access:"
    echo "  http://${NETWORK_NAME}.local"
    echo "  http://10.42.0.1"
    echo ""
    echo "Next Steps:"
    echo "1. Start service: sudo systemctl start ${SERVICE_NAME}.service"
    echo "2. Check status:  sudo systemctl status ${SERVICE_NAME}.service"
    echo "3. Connect to 'OM1-Setup' WiFi"
    echo "4. Access http://${NETWORK_NAME}.local"
    echo ""
}

main() {
    echo "=== OM1 WiFi Portal Installation ==="
    echo ""

    # Parse command line arguments
    parse_arguments "$@"

    echo "Configuration:"
    echo "  Network Name: ${NETWORK_NAME}"
    echo "  Local Address: ${NETWORK_NAME}.local"
    echo ""

    # Run installation steps
    check_root
    check_requirements
    install_avahi
    install_scripts
    configure_hotspot
    install_service
    setup_logging
    enable_service

    # Display summary
    display_summary

    log_success "Installation completed!"
}

main "$@"
