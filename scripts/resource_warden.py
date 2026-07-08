#!/data/data/com.termux/files/usr/bin/python3
"""
resource_warden.py — Resource monitoring daemon for Team B v1.1.0.
Monitors CPU, memory, and disk usage. Communicates with watchdog via Unix socket.
"""

import os
import sys
import time
import json
import socket
import logging
import psutil
from pathlib import Path

SOCKET_PATH = "/tmp/warden.sock"
LOG_DIR = Path(os.path.expanduser("~/team_b_deploy/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "resource_warden.log"
CPU_THRESHOLD = 85.0
MEMORY_THRESHOLD = 90.0
DISK_THRESHOLD = 95.0
CHECK_INTERVAL = 5.0

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def ensure_log_dir():
    """Ensure log directory exists."""
    log_dir = Path(LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)


def get_system_metrics():
    """Collect current system resource metrics."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "timestamp": time.time(),
    }


def check_thresholds(metrics):
    """Check if any resource exceeds thresholds."""
    alerts = []

    if metrics["cpu_percent"] > CPU_THRESHOLD:
        alerts.append(f"CPU usage high: {metrics['cpu_percent']:.1f}%")

    if metrics["memory_percent"] > MEMORY_THRESHOLD:
        alerts.append(f"Memory usage high: {metrics['memory_percent']:.1f}%")

    if metrics["disk_percent"] > DISK_THRESHOLD:
        alerts.append(f"Disk usage high: {metrics['disk_percent']:.1f}%")

    return alerts


def send_to_watchdog(message):
    """Send message to watchdog via Unix socket."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(SOCKET_PATH)
        sock.sendall(json.dumps(message).encode("utf-8"))
        sock.close()
        return True
    except (socket.error, ConnectionRefusedError) as e:
        logger.warning(f"Failed to send to watchdog: {e}")
        return False


def run_daemon():
    """Main daemon loop."""
    ensure_log_dir()
    logger.info("Resource Warden started")

    # Remove stale socket if exists
    if os.path.exists(SOCKET_PATH):
        try:
            os.unlink(SOCKET_PATH)
        except OSError:
            pass

    while True:
        try:
            metrics = get_system_metrics()
            alerts = check_thresholds(metrics)

            if alerts:
                for alert in alerts:
                    logger.warning(alert)

                # Notify watchdog about resource issues
                message = {
                    "type": "resource_alert",
                    "metrics": metrics,
                    "alerts": alerts,
                }
                send_to_watchdog(message)
            else:
                logger.debug(
                    f"Resources OK - CPU: {metrics['cpu_percent']:.1f}%, "
                    f"Mem: {metrics['memory_percent']:.1f}%, "
                    f"Disk: {metrics['disk_percent']:.1f}%"
                )

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Resource Warden stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in resource monitoring: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run_daemon()
