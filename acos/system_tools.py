from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

import psutil


def _gpu_status() -> dict[str, Any]:
    if not shutil.which("nvidia-smi"):
        return {"available": False, "vendor": None}
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()
        devices = []
        for line in out.splitlines():
            name, total, used, util = [x.strip() for x in line.split(",", 3)]
            devices.append(
                {
                    "name": name,
                    "memory_total_mb": int(total),
                    "memory_used_mb": int(used),
                    "utilization_percent": int(util),
                }
            )
        return {"available": True, "vendor": "NVIDIA", "devices": devices}
    except Exception as exc:  # telemetry must never crash ACOS
        return {"available": False, "error": str(exc)}


def system_status() -> dict[str, Any]:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.cwd()))
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu": {
            "logical_cores": os.cpu_count(),
            "load_percent": psutil.cpu_percent(interval=0.05),
        },
        "memory": {
            "total_gb": round(vm.total / 1024**3, 2),
            "available_gb": round(vm.available / 1024**3, 2),
            "used_percent": vm.percent,
        },
        "disk": {
            "total_gb": round(disk.total / 1024**3, 2),
            "free_gb": round(disk.free / 1024**3, 2),
            "used_percent": disk.percent,
        },
        "gpu": _gpu_status(),
    }


def list_workspace(workspace: Path) -> list[dict[str, Any]]:
    workspace = workspace.resolve()
    items: list[dict[str, Any]] = []
    for entry in sorted(workspace.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:200]:
        resolved = entry.resolve()
        if workspace not in resolved.parents and resolved != workspace:
            continue
        items.append(
            {
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else None,
            }
        )
    return items
