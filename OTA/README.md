# OTA Setup Instructions

The OTA (Over-The-Air) update system allows you to remotely update the software on your device. This guide will walk you through the steps to set up OTA updates using TailScale and Portainer agent.

## Prerequisites

Install TailScale on your device. Follow the instructions on the [TailScale website](https://tailscale.com/download) to download and install the appropriate package for your operating system.

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

Start and authenticate TailScale:

```bash
sudo tailscale up
```

Verify TailScale is running:

```bash
tailscale status
```

You should see your device listed with its TailScale IP address.

## Install Portainer Agent

Pull the Portainer Agent Docker image:

```bash
git clone https://github.com/OpenMind/orin-system-setup.git

cd orin-system-setup/OTA
```

Run the Portainer Agent container:

```bash
docker-compose up -d
```

Verify the Portainer Agent is running:

```bash
docker ps
```

You should see the `portainer/agent` container listed.
