import json
import logging

logging.basicConfig(level=logging.INFO)


class ProgressReporter:
    """Handles progress reporting for OTA operations."""

    def __init__(self, ws_client=None):
        """
        Initialize ProgressReporter.

        Parameters
        ----------
        ws_client : WebSocketClient, optional
            WebSocket client for sending progress updates
        """
        self.ws_client = ws_client

    def send_progress_update(self, status: str, message: str, progress: int):
        """
        Send progress update through WebSocket.

        Parameters
        ----------
        status : str
            Current status of the operation
        message : str
            Progress message
        progress : int
            Progress percentage (0-100)
        """
        if self.ws_client:
            update_data = {
                "type": "ota_progress",
                "status": status,
                "message": message,
                "progress": progress,
                "timestamp": json.dumps(
                    None
                ),  # Will be set by json.dumps with current time
            }
            try:
                self.ws_client.send_message(json.dumps(update_data))
                logging.info(
                    f"Sent progress update: {status} - {message} ({progress}%)"
                )
            except Exception as e:
                logging.warning(f"Failed to send progress update: {e}")

    def set_ws_client(self, ws_client):
        """
        Set or update the WebSocket client.

        Parameters
        ----------
        ws_client : WebSocketClient
            WebSocket client for sending progress updates
        """
        self.ws_client = ws_client
