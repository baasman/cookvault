"""System metrics API endpoints for monitoring and load testing"""

import os
import time
from typing import Tuple

import psutil
from flask import Blueprint, Response, jsonify

from app.api.auth import require_admin, require_auth
from app.models.user import User

bp = Blueprint("system", __name__, url_prefix="/system")


@bp.route("/metrics", methods=["GET"])
@require_auth
@require_admin
def get_system_metrics(current_user: User) -> Tuple[Response, int]:
    """
    Get system metrics including memory and CPU usage.

    Only accessible to admin users for security reasons.
    Useful for load testing and monitoring.
    """
    try:
        # Get current process
        process = psutil.Process(os.getpid())

        # Memory information
        memory_info = process.memory_info()
        system_memory = psutil.virtual_memory()

        # CPU information
        cpu_percent = process.cpu_percent(interval=0.1)
        system_cpu = psutil.cpu_percent(interval=0.1, percpu=False)

        # Convert bytes to MB for readability
        def bytes_to_mb(bytes_val: int) -> float:
            return round(bytes_val / (1024 * 1024), 2)

        metrics = {
            "process": {
                "memory": {
                    "rss_mb": bytes_to_mb(memory_info.rss),  # Resident Set Size
                    "vms_mb": bytes_to_mb(memory_info.vms),  # Virtual Memory Size
                    "percent": round(process.memory_percent(), 2),
                },
                "cpu_percent": round(cpu_percent, 2),
                "num_threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections()),
            },
            "system": {
                "memory": {
                    "total_mb": bytes_to_mb(system_memory.total),
                    "available_mb": bytes_to_mb(system_memory.available),
                    "used_mb": bytes_to_mb(system_memory.used),
                    "percent": round(system_memory.percent, 2),
                },
                "cpu_percent": round(system_cpu, 2),
                "cpu_count": psutil.cpu_count(),
            },
            "timestamp": time.time(),
        }

        return jsonify(metrics), 200

    except Exception as e:
        return jsonify({"error": f"Failed to get system metrics: {str(e)}"}), 500
