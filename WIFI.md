# WiFi Setup

## Install dependencies

```bash
sudo apt update
sudo apt install -y network-manager dnsmasq hostapd python3-flask avahi-daemon avahi-utils libnss-mdns
```

## Enable NetworkManager

```bash
sudo systemctl stop wpa_supplicant
sudo systemctl disable wpa_supplicant
sudo systemctl enable NetworkManager
```

Modify NetworkManager configuration to allow hotspot creation:

```bash
sudo vim /etc/NetworkManager/conf.d/00-hotspot.conf
```

Add the following lines:

```
[device]
wifi.scan-rand-mac-address=no

[connection]
wifi.cloned-mac-address=permanent
```

## Enable hotspot

Create a entrypoint for starting the hotspot on boot:

```bash
sudo vim /usr/local/bin/start_hotspot.sh
```

```bash
#!/bin/bash
SSID="OpenMind-Setup-$(hostname | cut -c1-4)"
PASS="OpenMind123"
nmcli device wifi hotspot ifname wlP1p1s0 ssid "$SSID" password "$PASS"

sleep 3

/usr/local/bin/setup_captive.sh

systemctl start om-wifi-portal
```

Make it executable:

```bash
sudo chmod +x /usr/local/bin/start_hotspot.sh
```

## Add a Flask frontend for the captive portal

Create the Flask app:

```bash
sudo vim /opt/om_wifi_portal/portal.py
```

```python
#!/usr/bin/env python3
from flask import Flask, render_template_string, request, redirect
import subprocess

app = Flask(__name__)

HTML = """
<!doctype html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>OM1 Setup</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, Arial; max-width: 400px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { margin: 0 0 20px; color: #333; }
        input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
        button { width: 100%; padding: 14px; background: #4CAF50; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; margin-top: 10px; }
        button:active { background: #45a049; }
        .scanning { text-align: center; color: #666; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🤖 OM1 Wi-Fi Setup</h2>
        <form method="post">
            <input name="ssid" placeholder="Network Name (SSID)" required autofocus>
            <input name="password" type="password" placeholder="Password (leave empty if none)">
            <button type="submit">Connect</button>
        </form>
    </div>
</body>
</html>
"""

# Captive portal detection endpoints
@app.route("/generate_204")  # Android
@app.route("/gen_204")
@app.route("/hotspot-detect.html")  # iOS/macOS
@app.route("/connecttest.txt")  # Windows
@app.route("/success.txt")
@app.route("/ncsi.txt")
def captive_redirect():
    return redirect("/", code=302)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        ssid = request.form["ssid"].strip()
        password = request.form.get("password", "").strip()

        cmd = ["nmcli", "device", "wifi", "connect", ssid, "ifname", "wlP1p1s0"]
        if password:
            cmd.extend(["password", password])

        try:
            subprocess.run(cmd, check=True, timeout=20, capture_output=True)
            return """
            <html>
            <head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body style='font-family: Arial; text-align: center; padding: 50px; background: #f5f5f5;'>
                <div style='background: white; padding: 40px; border-radius: 10px; display: inline-block;'>
                    <h2 style='color: #4CAF50;'>✅ Connected!</h2>
                    <p>OM1 is now connected to <strong>{}</strong></p>
                    <p style='color: #666;'>You can close this window.</p>
                </div>
            </body>
            </html>
            """.format(ssid)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else "Unknown error"
            return """
            <html>
            <head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body style='font-family: Arial; text-align: center; padding: 50px; background: #f5f5f5;'>
                <div style='background: white; padding: 40px; border-radius: 10px; display: inline-block;'>
                    <h2 style='color: #f44336;'>❌ Connection Failed</h2>
                    <p>Could not connect to <strong>{}</strong></p>
                    <p style='color: #666; font-size: 14px;'>Check the password and try again</p>
                    <a href='/' style='color: #4CAF50; text-decoration: none;'>← Try Again</a>
                </div>
            </body>
            </html>
            """.format(ssid)

    return HTML

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
```

## Start the portal on boot

```bash
sudo vim /etc/systemd/system/om-wifi-portal.service
```

```
[Unit]
Description=OM1 Wi-Fi Captive Portal
After=network-online.target

[Service]
ExecStart=/usr/bin/python3 /opt/om_wifi_portal/portal.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable om-wifi-portal
```

## Setup WiFi checker

Create the WiFi checker script:

```bash
sudo vim /usr/local/bin/om-wifi-check.sh
```

```bash
#!/bin/bash
DEVICE="wlP1p1s0"

echo "Waiting for NetworkManager..."
for i in {1..20}; do
  if nmcli general status | grep -q "running"; then break; fi
  sleep 1
done

echo "Waiting for WiFi device..."
for i in {1..30}; do
  if nmcli device status | grep -q "$DEVICE"; then
    echo "WiFi device found!"
    break
  fi
  sleep 1
done

if nmcli -t -f DEVICE,STATE device | grep -q "$DEVICE:connected"; then
  echo "Wi-Fi already connected."
  iptables -t nat -F PREROUTING 2>/dev/null
  systemctl stop om-wifi-portal
else
  echo "No Wi-Fi. Starting hotspot..."
  /usr/local/bin/start_hotspot.sh
fi
```

Make it executable:

```bash
sudo chmod +x /usr/local/bin/om-wifi-check.sh
```

Create a service to run the WiFi checker on boot:

```bash
sudo vim /etc/systemd/system/om-wifi-check.service
```

```
[Unit]
Description=OM Wi-Fi Auto Check
After=NetworkManager.service
Wants=NetworkManager.service
After=sys-subsystem-net-devices-wlP1p1s0.device
Wants=sys-subsystem-net-devices-wlP1p1s0.device

[Service]
ExecStart=/usr/local/bin/om-wifi-check.sh
Type=oneshot
ExecStartPre=/bin/sleep 5

[Install]
WantedBy=multi-user.target
```

Enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable om-wifi-check
```

## Setup captive DNS

Create the captive DNS setup script:

```bash
sudo vim /usr/local/bin/setup_captive.sh
```

```bash
#!/bin/bash
# Clear existing rules
iptables -t nat -F PREROUTING 2>/dev/null

# Redirect all HTTP/HTTPS traffic to Flask portal
iptables -t nat -A PREROUTING -i wlP1p1s0 -p tcp --dport 80 -j REDIRECT --to-port 80
iptables -t nat -A PREROUTING -i wlP1p1s0 -p tcp --dport 443 -j REDIRECT --to-port 80

echo "Captive portal redirect setup complete"
```

Make it executable:
```bash
sudo chmod +x /usr/local/bin/setup_captive.sh
```

## Setup mDNS
Start and enable the Avahi daemon for mDNS support:

```bash
sudo systemctl enable avahi-daemon
sudo systemctl restart avahi-daemon
```

You can verify it’s running:

```bash
systemctl status avahi-daemon
```

You should see **active (running)**.

Now, check your device's hostname:

```bash
hostnamectl
```

If it’s not om1, set it:

```bash
sudo hostnamectl set-hostname om1
```

Then restart Avahi:

```bash
sudo systemctl restart avahi-daemon
```

You should now be able to access your device at `http://om1.local` from other devices on the same network.
