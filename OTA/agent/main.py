import logging
import time
import os

from ..utils.ota import BaseOTA

OTA_SERVER_URL = os.getenv("OTA_SERVER_URL", "wss://api.openmind.org/api/v1/ota/agent")
OM_API_KEY = os.getenv("OM_API_KEY")
OM_API_KEY_ID = os.getenv("OM_API_KEY_ID")

logging.basicConfig(level=logging.INFO)


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

        ota = BaseOTA(
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
