import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

from .s3_utils import S3FileDownloader
from .ws_client import WebSocketClient

logging.basicConfig(level=logging.INFO)


class BaseOTA:
    def __init__(
        self, ota_server_url: str, om_api_key: str, om_api_key_id: str
    ) -> None:
        self.ota_server_url = ota_server_url
        self.om_api_key = om_api_key
        self.om_api_key_id = om_api_key_id

        if not self.ota_server_url or not self.om_api_key or not self.om_api_key_id:
            raise ValueError("OTA server URL and API keys must be provided")

        self.ws_client = self.create_ws_client()

    def create_ws_client(self) -> WebSocketClient:
        """
        Factory function to create a WebSocketClient instance.
        """
        return WebSocketClient(
            url=f"{self.ota_server_url}?api_key_id={self.om_api_key_id}&api_key={self.om_api_key}"
        )

    def apply_ota_update(
        self,
        service_name: str,
        yaml_content: dict,
        temp_yaml_path: str,
        tag: str,
        ws_client=None,
    ):
        """
        Apply the OTA update based on the YAML content.

        Parameters
        ----------
        service_name : str
            The name of the service to be updated
        yaml_content : dict
            The parsed YAML content containing update instructions
        temp_yaml_path : str
            The temporary path of the downloaded YAML file
        tag : str
            The update tag/version
        ws_client : WebSocketClient, optional
            WebSocket client for sending progress updates
        """
        logging.info(f"Applying OTA update {tag} with content: {yaml_content}")

        self.send_progress_update(
            ws_client, "starting", f"Starting OTA update {tag}", 0
        )

        updates_dir = os.path.abspath(".ota")
        os.makedirs(updates_dir, mode=0o755, exist_ok=True)

        try:
            logging.info("Stopping current Docker services...")
            self.send_progress_update(
                ws_client, "stopping", "Stopping current Docker services", 10
            )
            stop_result = self.stop_docker_services(yaml_content)
            if not stop_result.get("success"):
                error_msg = f"Failed to stop Docker services: {stop_result.get('error', 'Unknown error')}"
                logging.error(error_msg)
                self.send_progress_update(ws_client, "error", error_msg, 10)

            self.send_progress_update(ws_client, "storing", "Storing update files", 20)
            stored_version_yaml_path = os.path.join(
                updates_dir, f"{service_name}_{tag}.yaml"
            )
            stored_latest_yaml_path = os.path.join(
                updates_dir, f"{service_name}_latest.yaml"
            )

            try:
                shutil.copy2(temp_yaml_path, stored_version_yaml_path)
                shutil.copy2(temp_yaml_path, stored_latest_yaml_path)
                logging.info(
                    f"Stored OTA update files: {stored_version_yaml_path}, {stored_latest_yaml_path}"
                )
            except Exception as e:
                error_msg = f"Failed to store OTA update file: {e}"
                logging.error(error_msg)
                self.send_progress_update(ws_client, "error", error_msg, 20)
                return False

            logging.info("Starting updated Docker services...")
            start_result = self.start_docker_services(yaml_content, ws_client)
            if not start_result.get("success"):
                error_msg = f"Failed to start Docker services: {start_result.get('error', 'Unknown error')}"
                logging.error(error_msg)
                self.send_progress_update(ws_client, "error", error_msg, 80)
                return False

            logging.info(f"Successfully applied OTA update {tag}")
            self.send_progress_update(
                ws_client, "completed", f"Successfully applied OTA update {tag}", 100
            )
            return True

        except Exception as e:
            error_msg = f"Unexpected error during OTA update: {e}"
            logging.error(error_msg)
            self.send_progress_update(ws_client, "error", error_msg, 0)
            return False

    def stop_docker_services(self, yaml_content: dict) -> dict:
        """
        Stop Docker containers/services based on the update configuration.

        Parameters
        ----------
        yaml_content : dict
            The parsed YAML content containing service definitions

        Returns
        -------
        dict
            Result with success status and error information
        """
        try:
            services = yaml_content.get("services", {})

            if not services:
                logging.warning("No services defined in update YAML")
                return {"success": True, "message": "No services to stop"}

            stopped_services = []
            failed_services = []

            for service_name, service_config in services.items():
                try:
                    container_name = service_config.get("container_name", service_name)

                    check_cmd = [
                        "docker",
                        "ps",
                        "-q",
                        "--filter",
                        f"name={container_name}",
                    ]
                    check_result = subprocess.run(
                        check_cmd, capture_output=True, text=True, timeout=10
                    )

                    if check_result.returncode == 0 and check_result.stdout.strip():
                        stop_cmd = ["docker", "stop", container_name]
                        stop_result = subprocess.run(
                            stop_cmd, capture_output=True, text=True, timeout=30
                        )

                        if stop_result.returncode == 0:
                            logging.info(f"Stopped container: {container_name}")
                            stopped_services.append(container_name)
                        else:
                            logging.error(
                                f"Failed to stop container {container_name}: {stop_result.stderr}"
                            )
                            failed_services.append(container_name)
                    else:
                        logging.info(
                            f"Container {container_name} not running or doesn't exist"
                        )

                except subprocess.TimeoutExpired:
                    logging.error(f"Timeout stopping service {service_name}")
                    failed_services.append(service_name)
                except Exception as e:
                    logging.error(f"Error stopping service {service_name}: {e}")
                    failed_services.append(service_name)

            if failed_services:
                return {
                    "success": False,
                    "error": f"Failed to stop services: {', '.join(failed_services)}",
                    "stopped": stopped_services,
                    "failed": failed_services,
                }

            return {
                "success": True,
                "message": f"Successfully stopped {len(stopped_services)} services",
                "stopped": stopped_services,
            }

        except Exception as e:
            logging.error(f"Error in stop_docker_services: {e}")
            return {"success": False, "error": str(e)}

    def pull_images_with_progress(self, pull_cmd: list, ws_client=None) -> dict:
        """
        Pull Docker images with real-time progress reporting.

        Parameters
        ----------
        pull_cmd : list
            The docker-compose pull command
        ws_client : WebSocketClient, optional
            WebSocket client for sending progress updates

        Returns
        -------
        dict
            Result with success status and output information
        """
        try:
            process = subprocess.Popen(
                pull_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            stdout_lines = []
            services_found = set()
            services_pulled = set()
            current_service = None

            while True:
                if process.stdout is None:
                    break
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break

                if output:
                    stdout_lines.append(output.strip())
                    line = output.strip()
                    logging.info(f"Docker pull output: {line}")

                    if "Pulling" in line:
                        # Extract service name from "Pulling service_name..." or similar patterns
                        service_match = re.search(r"Pulling\s+(\w+)", line)
                        if service_match:
                            current_service = service_match.group(1)
                            services_found.add(current_service)
                            progress = 30 + (
                                len(services_pulled) * 40 // max(len(services_found), 1)
                            )
                            self.send_progress_update(
                                ws_client,
                                "pulling_service",
                                f"Pulling {current_service}",
                                progress,
                            )
                        elif not service_match and current_service is None:
                            # Generic pulling message
                            self.send_progress_update(
                                ws_client, "pulling", f"Pulling: {line}", 35
                            )

                    elif "Pull complete" in line or "Already exists" in line:
                        if current_service:
                            services_pulled.add(current_service)
                            progress = 30 + (
                                len(services_pulled) * 40 // max(len(services_found), 1)
                            )
                            self.send_progress_update(
                                ws_client,
                                "pulled_service",
                                f"Completed pulling {current_service}",
                                progress,
                            )
                            current_service = None

                    elif "Downloading" in line:
                        # Show downloading progress if available
                        download_match = re.search(
                            r"Downloading\s+([\w.]+)\s+(\d+\.\d+\w+)\s*/\s*(\d+\.\d+\w+)",
                            line,
                        )
                        if download_match and current_service:
                            layer, current_size, total_size = download_match.groups()
                            self.send_progress_update(
                                ws_client,
                                "downloading",
                                f"Downloading {current_service}: {current_size}/{total_size}",
                                30
                                + (
                                    len(services_pulled)
                                    * 40
                                    // max(len(services_found), 1)
                                ),
                            )

                    elif "Extracting" in line and current_service:
                        self.send_progress_update(
                            ws_client,
                            "extracting",
                            f"Extracting {current_service}",
                            30
                            + (
                                len(services_pulled) * 40 // max(len(services_found), 1)
                            ),
                        )

            # Wait for process to complete and get any remaining output
            stdout_remainder, stderr_output = process.communicate()
            if stdout_remainder:
                stdout_lines.extend(stdout_remainder.strip().split("\n"))

            return_code = (
                process.returncode
                if process.returncode is not None
                else process.wait(timeout=900)
            )

            stdout_text = "\n".join(stdout_lines)
            stderr_text = stderr_output or ""

            if return_code == 0:
                logging.info("Successfully pulled all Docker images")
                return {
                    "success": True,
                    "message": "Successfully pulled all images",
                    "output": stdout_text,
                    "services_pulled": list(services_pulled),
                }
            else:
                error_msg = f"Pull failed with return code {return_code}: {stderr_text}"
                logging.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "output": stdout_text,
                    "stderr": stderr_text,
                }

        except subprocess.TimeoutExpired:
            process.kill()
            error_msg = "Docker pull operation timed out"
            logging.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output": "\n".join(stdout_lines) if "stdout_lines" in locals() else "",
            }
        except Exception as e:
            error_msg = f"Error during pull operation: {e}"
            logging.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output": "\n".join(stdout_lines) if "stdout_lines" in locals() else "",
            }

    def start_docker_services(self, yaml_content: dict, ws_client=None) -> dict:
        """
        Start Docker containers/services based on the update configuration.

        Parameters
        ----------
        yaml_content : dict
            The parsed YAML content containing service definitions
        ws_client : WebSocketClient, optional
            WebSocket client for sending progress updates

        Returns
        -------
        dict
            Result with success status and error information
        """
        try:
            services = yaml_content.get("services", {})

            if not services:
                logging.warning("No services defined in update YAML")
                return {"success": True, "message": "No services to start"}

            temp_compose_file = None
            try:
                temp_compose_file = self.create_temp_compose_file(yaml_content)

                logging.info("Pulling Docker images...")
                self.send_progress_update(
                    ws_client, "pulling", "Starting to pull Docker images", 30
                )

                pull_cmd = ["docker-compose", "-f", temp_compose_file, "pull"]
                pull_result = self.pull_images_with_progress(pull_cmd, ws_client)

                if not pull_result.get("success"):
                    return {
                        "success": False,
                        "error": f"docker-compose pull failed: {pull_result.get('error')}",
                        "output": pull_result.get("output", ""),
                    }

                logging.info("Successfully pulled Docker images")
                self.send_progress_update(
                    ws_client, "pulled", "Successfully pulled Docker images", 70
                )

                logging.info("Starting Docker services...")
                self.send_progress_update(
                    ws_client, "starting_services", "Starting Docker services", 80
                )
                up_cmd = ["docker-compose", "-f", temp_compose_file, "up", "-d", "--no-build"]
                up_result = subprocess.run(
                    up_cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minutes timeout for starting
                )

                if up_result.returncode == 0:
                    logging.info("Successfully started services with docker-compose")

                    # Clean up old images after successful deployment
                    cleanup_result = self.cleanup_old_images(ws_client)

                    return {
                        "success": True,
                        "message": "Successfully pulled images and started updated services",
                        "pull_output": pull_result.get("output", ""),
                        "up_output": up_result.stdout,
                        "cleanup_result": cleanup_result,
                    }
                else:
                    logging.error(f"Failed to start services: {up_result.stderr}")
                    return {
                        "success": False,
                        "error": f"docker-compose up failed: {up_result.stderr}",
                        "pull_output": pull_result.get("output", ""),
                        "up_output": up_result.stdout,
                    }

            finally:
                if temp_compose_file and os.path.exists(temp_compose_file):
                    try:
                        os.unlink(temp_compose_file)
                    except OSError as e:
                        logging.warning(
                            f"Failed to clean up temporary compose file: {e}"
                        )

        except subprocess.TimeoutExpired:
            logging.error("Timeout starting Docker services")
            return {"success": False, "error": "Timeout starting services"}
        except Exception as e:
            logging.error(f"Error in start_docker_services: {e}")
            return {"success": False, "error": str(e)}

    def create_temp_compose_file(self, yaml_content: dict) -> str:
        """
        Create a temporary docker-compose file from YAML content.

        Parameters
        ----------
        yaml_content : dict
            The parsed YAML content

        Returns
        -------
        str
            Path to the temporary docker-compose file
        """
        import yaml

        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
        try:
            yaml.dump(yaml_content, temp_file, default_flow_style=False)
            temp_file.flush()
            logging.info(f"Created temporary docker-compose file: {temp_file.name}")
            return temp_file.name
        finally:
            temp_file.close()

    def cleanup_old_images(self, ws_client=None) -> dict:
        """
        Clean up old, unused Docker images to free up disk space.

        Parameters
        ----------
        ws_client : WebSocketClient, optional
            WebSocket client for sending progress updates

        Returns
        -------
        dict
            Result with success status and cleanup information
        """
        try:
            logging.info("Cleaning up old Docker images...")
            self.send_progress_update(
                ws_client, "cleanup", "Cleaning up old Docker images", 90
            )

            cleanup_cmds = [
                ["docker", "image", "prune", "-f"],
                ["docker", "container", "prune", "-f"],
                ["docker", "system", "prune", "-f"],
            ]

            cleanup_results = []
            total_space_freed = "0B"

            for cmd_name, cmd in zip(["images", "containers", "system"], cleanup_cmds):
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=60
                    )

                    if result.returncode == 0:
                        output = result.stdout.strip()
                        cleanup_results.append(
                            {"command": cmd_name, "success": True, "output": output}
                        )

                        if "Total reclaimed space:" in output:
                            space_match = re.search(
                                r"Total reclaimed space:\s*([\d.]+\w+)", output
                            )
                            if space_match:
                                total_space_freed = space_match.group(1)

                        logging.info(f"Successfully cleaned up {cmd_name}: {output}")
                    else:
                        cleanup_results.append(
                            {
                                "command": cmd_name,
                                "success": False,
                                "error": result.stderr,
                            }
                        )
                        logging.warning(
                            f"Failed to cleanup {cmd_name}: {result.stderr}"
                        )

                except subprocess.TimeoutExpired:
                    cleanup_results.append(
                        {
                            "command": cmd_name,
                            "success": False,
                            "error": "Cleanup timeout",
                        }
                    )
                    logging.warning(f"Timeout during {cmd_name} cleanup")
                except Exception as e:
                    cleanup_results.append(
                        {"command": cmd_name, "success": False, "error": str(e)}
                    )
                    logging.warning(f"Error during {cmd_name} cleanup: {e}")

            successful_cleanups = [r for r in cleanup_results if r["success"]]

            if successful_cleanups:
                message = (
                    f"Cleaned up Docker resources. Space freed: {total_space_freed}"
                )
                logging.info(message)
                self.send_progress_update(ws_client, "cleanup_complete", message, 95)
                return {
                    "success": True,
                    "message": message,
                    "space_freed": total_space_freed,
                    "cleanup_results": cleanup_results,
                }
            else:
                message = "Cleanup completed but no space was freed"
                logging.info(message)
                return {
                    "success": True,
                    "message": message,
                    "space_freed": "0B",
                    "cleanup_results": cleanup_results,
                }

        except Exception as e:
            error_msg = f"Error during Docker cleanup: {e}"
            logging.error(error_msg)
            self.send_progress_update(ws_client, "cleanup_error", error_msg, 90)
            return {"success": False, "error": error_msg}

    def send_progress_update(self, ws_client, status: str, message: str, progress: int):
        """
        Send progress update through WebSocket.

        Parameters
        ----------
        ws_client : WebSocketClient
            WebSocket client to send updates through
        status : str
            Current status of the operation
        message : str
            Progress message
        progress : int
            Progress percentage (0-100)
        """
        if ws_client:
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
                ws_client.send_message(json.dumps(update_data))
                logging.info(
                    f"Sent progress update: {status} - {message} ({progress}%)"
                )
            except Exception as e:
                logging.warning(f"Failed to send progress update: {e}")

    def ota_process(self, message: str, ws_client=None):
        """
        Process OTA messages received from the WebSocket server.

        Parameters
        ----------
        message : str
            The message received from the WebSocket server.
        ws_client : WebSocketClient, optional
            WebSocket client for sending progress updates
        """
        if isinstance(message, str):
            logging.info(f"Received OTA update message: {message}")
            try:
                data = json.loads(message)
                logging.info(f"Processing OTA update data: {data}")

                # tag
                # s3 url
                # checksum
                # service name
                tag = data.get("tag")
                s3_url = data.get("s3_url")
                checksum = data.get("checksum")
                service_name = data.get("service_name")
                if not tag or not s3_url or not checksum or not service_name:
                    logging.error("Invalid OTA update message: missing required fields")
                    return

                logging.info(
                    f"OTA Update Details - Tag: {tag}, S3 URL: {s3_url}, Checksum: {checksum}, Service Name: {service_name}"
                )

                s3_downloader = S3FileDownloader()
                yaml_content, local_file_path = s3_downloader.download_and_verify_yaml(
                    s3_url=s3_url, expected_checksum=checksum, algorithm="sha256"
                )

                if yaml_content and local_file_path:
                    logging.info(
                        f"Successfully downloaded and verified YAML file: {local_file_path}"
                    )
                    logging.info(f"YAML content: {yaml_content}")

                    self.apply_ota_update(
                        service_name, yaml_content, local_file_path, tag, ws_client
                    )

                    try:
                        os.unlink(local_file_path)
                        logging.info("Cleaned up downloaded file")
                    except OSError as e:
                        logging.warning(
                            f"Failed to clean up file {local_file_path}: {e}"
                        )
                else:
                    logging.error("Failed to download or verify YAML file from S3")
                    self.send_progress_update(ws_client, "download_error", "Failed to download or verify YAML file from S3", 0)

            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON message: {e}")
                self.send_progress_update(ws_client, "decode_error", "Failed to decode message", 0)
        else:
            logging.warning("Received non-string message, ignoring.")
            self.send_progress_update(ws_client, "error_message", "Failed to decode message", 0)
