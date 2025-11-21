import json
import logging
import os
import subprocess
import threading
import time
from typing import Optional

import requests

from ..utils.ota import BaseOTA

OTA_SERVER_URL = os.getenv("OTA_SERVER_URL", "wss://api.openmind.org/api/v1/ota/agent")
DOCKER_CONTAINER_STATUS_URL = os.getenv(
    "DOCKER_STATUS_URL", "https://api.openmind.org/api/core/ota/agent/docker"
)
OM_API_KEY = os.getenv("OM_API_KEY")
OM_API_KEY_ID = os.getenv("OM_API_KEY_ID")

logging.basicConfig(level=logging.INFO)


class AgentOTA(BaseOTA):
    """
    OTA Agent class extending BaseOTA for specific agent functionalities.
    """

    def __init__(self, ota_server_url: str, om_api_key: str, om_api_key_id: str):
        super().__init__(ota_server_url, om_api_key, om_api_key_id)

        if not DOCKER_CONTAINER_STATUS_URL:
            logging.error(
                "DOCKER_CONTAINER_STATUS_URL environment variable must be set"
            )
            raise ValueError(
                "DOCKER_CONTAINER_STATUS_URL environment variable must be set"
            )

        self.container_names_url = f"{DOCKER_CONTAINER_STATUS_URL}/names"
        self.container_status_url = f"{DOCKER_CONTAINER_STATUS_URL}/status"
        self.container_names = [
            "om1",
            "om1_sensor",
            "orchestrator",
            "watchdog",
            "zenoh_bridge",
            "om1_avatar",
            "om1_monitor",
            "om1_video_processor",
            "ota_agent",
            "ota_updater",
        ]

        self.container_name_thread: Optional[threading.Thread] = None
        self.container_status_thread: Optional[threading.Thread] = None

        self.start_fetching_container_names()
        self.start_reporting_container_status()

    def _fetch_docker_name(self):
        """
        Fetch the list of Docker container names from the server.
        """
        try:
            response = requests.get(
                self.container_names_url,
                headers={"x-api-key": self.om_api_key},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            container_names = data.get("container_names", [])
            if container_names:
                self.container_names = container_names
            time.sleep(30)
        except Exception as e:
            logging.error(f"Failed to fetch Docker container names: {e}")
            time.sleep(5)

    def start_fetching_container_names(self):
        """
        Start the background thread for periodic Docker container names fetching.
        """
        if (
            self.container_name_thread is None
            or not self.container_name_thread.is_alive()
        ):
            self.container_name_thread = threading.Thread(
                target=self._fetch_docker_name, daemon=True
            )
            self.container_name_thread.start()
            logging.info(
                "Started periodic Docker container names fetching (every 30 seconds)"
            )
            return

        logging.info("Docker container names fetching thread is already running.")

    def read_container_status(self) -> Optional[dict]:
        """
        Read the status of Docker containers from the local Docker daemon.

        Returns
        -------
        Optional[dict]
            Dictionary with container statuses or None if failed
        """
        try:
            cmd = ["docker", "ps", "-a", "--format", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logging.error(f"Docker command failed: {result.stderr}")
                return None

            container_status = {}
            found_containers = set()

            for line in result.stdout.strip().split("\n"):
                if line:
                    try:
                        container_info = json.loads(line)
                        container_name = container_info.get("Names", "").strip()

                        if container_name in self.container_names:
                            found_containers.add(container_name)
                            container_status[container_name] = {
                                "status": container_info.get("State", "unknown"),
                                "image": container_info.get("Image", "unknown"),
                                "ports": container_info.get("Ports", ""),
                                "created": container_info.get("CreatedAt", ""),
                                "command": container_info.get("Command", ""),
                                "id": container_info.get("ID", ""),
                                "present": True,
                            }
                    except json.JSONDecodeError as e:
                        logging.warning(f"Failed to parse container info: {e}")
                        continue

            missing_containers = set(self.container_names) - found_containers
            for missing_container in missing_containers:
                container_status[missing_container] = {
                    "status": "missing",
                    "image": "unknown",
                    "ports": "",
                    "created": "",
                    "command": "",
                    "id": "",
                    "present": False,
                }
                logging.warning(
                    f"Container '{missing_container}' is missing from local Docker"
                )

            if missing_containers:
                logging.warning(f"Missing containers: {', '.join(missing_containers)}")

            logging.info(
                f"Successfully fetched status for {len(found_containers)} local containers, {len(missing_containers)} missing"
            )
            return container_status

        except subprocess.TimeoutExpired:
            logging.error("Docker command timed out")
            return None
        except FileNotFoundError:
            logging.error(
                "Docker command not found. Make sure Docker is installed and in PATH"
            )
            return None
        except Exception as e:
            logging.error(f"Failed to read local Docker container status: {e}")
            return None

    def _report_container_status(self):
        """
        Report the Docker container status to the server periodically.
        """
        while True:
            status = self.read_container_status()
            if status is not None:
                try:
                    response = requests.post(
                        self.container_status_url,
                        headers={
                            "x-api-key": self.om_api_key,
                            "Content-Type": "application/json",
                        },
                        json={"container_status": status},
                        timeout=10,
                    )
                    response.raise_for_status()
                    logging.info(
                        "Successfully reported Docker container status to server"
                    )
                except Exception as e:
                    logging.error(f"Failed to report Docker container status: {e}")
            time.sleep(30)

    def start_reporting_container_status(self):
        """
        Start the background thread for periodic Docker container status reporting.
        """
        if (
            self.container_status_thread is None
            or not self.container_status_thread.is_alive()
        ):
            self.container_status_thread = threading.Thread(
                target=self._report_container_status, daemon=True
            )
            self.container_status_thread.start()
            logging.info(
                "Started periodic Docker container status reporting (every 30 seconds)"
            )
            return

        logging.info("Docker container status reporting thread is already running.")


def main():
    """
    Main function to run the OTA updater WebSocket client.
    """
    try:
        if not OM_API_KEY or not OM_API_KEY_ID:
            logging.error(
                "OM_API_KEY and OM_API_KEY_ID environment variables must be set"
            )
            exit(1)

        ota = AgentOTA(
            ota_server_url=OTA_SERVER_URL,
            om_api_key=OM_API_KEY,
            om_api_key_id=OM_API_KEY_ID,
        )

        def callback_with_client(message):
            return ota.ota_process(message, ota.ws_client)

        ota.ws_client.register_message_callback(callback_with_client)
        ota.ws_client.connect()

        while True:
            time.sleep(5)

    except Exception as e:
        logging.error(f"Failed to connect to OTA server: {e}")


if __name__ == "__main__":
    main()
