"""Apple Silicon MPS auto-resolution, unified memory telemetry, and device utilities."""

from typing import Dict, Any, Optional, Tuple, Union
import os
import platform
import psutil
import torch


def resolve_device(preferred: Optional[Union[str, torch.device]] = None) -> torch.device:
    """Resolves hardware compute device with Apple Silicon MPS priority and CPU fallback.

    Args:
        preferred: Optional preferred device string ('mps', 'cuda', 'cpu', 'auto') or torch.device.

    Returns:
        Resolved torch.device.
    """
    if isinstance(preferred, torch.device):
        return preferred

    mps_available = bool(torch.backends.mps.is_available() and torch.backends.mps.is_built())

    if preferred is not None and preferred != "auto":
        pref = str(preferred).lower().strip()
        if pref == "mps":
            return torch.device("mps") if mps_available else torch.device("cpu")
        elif pref == "cuda":
            return torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        elif pref == "cpu":
            return torch.device("cpu")
        else:
            # Fallback for unknown/unsupported devices (e.g., 'tpu')
            return torch.device("cpu")

    # Automatic priority resolution:
    if mps_available:
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def get_memory_stats(device: Optional[Union[str, torch.device]] = None) -> Dict[str, Any]:
    """Collects host RAM and device GPU memory telemetry.

    Returns metrics formatted in MB and GB with 4.0 GB ceiling check.
    """
    if device is None:
        dev = resolve_device()
    elif isinstance(device, str):
        dev = resolve_device(device)
    else:
        dev = device

    vm = psutil.virtual_memory()
    proc = psutil.Process(os.getpid())
    rss_bytes = proc.memory_info().rss
    rss_mb = rss_bytes / (1024.0 * 1024.0)
    rss_gb = rss_bytes / (1024.0 ** 3)

    ram_total_gb = vm.total / (1024.0 ** 3)
    ram_used_gb = vm.used / (1024.0 ** 3)
    ram_available_gb = vm.available / (1024.0 ** 3)

    mps_alloc_bytes = 0
    mps_driver_bytes = 0
    cuda_alloc_bytes = 0

    mps_available = bool(torch.backends.mps.is_available() and torch.backends.mps.is_built())

    if dev.type == "mps" and mps_available:
        try:
            if hasattr(torch.mps, "current_allocated_memory"):
                mps_alloc_bytes = torch.mps.current_allocated_memory()
            if hasattr(torch.mps, "driver_allocated_memory"):
                mps_driver_bytes = torch.mps.driver_allocated_memory()
        except Exception:
            pass

    if dev.type == "cuda" and torch.cuda.is_available():
        try:
            cuda_alloc_bytes = torch.cuda.memory_allocated()
        except Exception:
            pass

    mps_alloc_mb = mps_alloc_bytes / (1024.0 * 1024.0)
    mps_alloc_gb = mps_alloc_bytes / (1024.0 ** 3)
    mps_driver_mb = mps_driver_bytes / (1024.0 * 1024.0)
    mps_driver_gb = mps_driver_bytes / (1024.0 ** 3)
    cuda_alloc_gb = cuda_alloc_bytes / (1024.0 ** 3)

    limit_gb = 4.0
    within_budget = rss_gb <= limit_gb

    return {
        "process_rss_mb": round(rss_mb, 2),
        "process_rss_gb": round(rss_gb, 4),
        "system_ram_total_gb": round(ram_total_gb, 2),
        "system_ram_used_gb": round(ram_used_gb, 2),
        "system_ram_available_gb": round(ram_available_gb, 2),
        "ram_total_gb": round(ram_total_gb, 2),
        "ram_used_gb": round(ram_used_gb, 2),
        "ram_available_gb": round(ram_available_gb, 2),
        "mps_allocated_bytes": mps_alloc_bytes,
        "mps_allocated_mb": round(mps_alloc_mb, 2),
        "mps_allocated_gb": round(mps_alloc_gb, 6),
        "mps_driver_bytes": mps_driver_bytes,
        "mps_driver_mb": round(mps_driver_mb, 2),
        "mps_driver_gb": round(mps_driver_gb, 6),
        "cuda_allocated_gb": round(cuda_alloc_gb, 6),
        "unified_memory_limit_gb": limit_gb,
        "within_memory_budget": within_budget,
        "device": str(dev),
        "device_type": dev.type,
        "mps_available": mps_available,
        "mps_built": bool(getattr(torch.backends.mps, "is_built", lambda: False)()),
        "platform": f"{platform.system()} {platform.machine()}",
    }


def check_memory_limit(
    max_limit_gb: float = 4.0,
    device: Optional[Union[str, torch.device]] = None
) -> Tuple[bool, float, Dict[str, Any]]:
    """Checks whether host RSS + device memory exceeds max_limit_gb."""
    stats = get_memory_stats(device)
    usage_gb = stats["process_rss_gb"] + stats["mps_allocated_gb"] + stats["cuda_allocated_gb"]
    within_limit = usage_gb <= max_limit_gb
    return within_limit, round(usage_gb, 4), stats


def empty_device_cache(device: Optional[Union[str, torch.device]] = None) -> None:
    """Frees cached memory on the target compute device."""
    dev = resolve_device(device) if device is not None else resolve_device()
    if dev.type == "mps":
        if hasattr(torch.mps, "empty_cache"):
            try:
                torch.mps.empty_cache()
            except Exception:
                pass
    elif dev.type == "cuda":
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass


def sync_device(device: Optional[Union[str, torch.device]] = None) -> None:
    """Blocks until asynchronous device kernels finish execution."""
    dev = resolve_device(device) if device is not None else resolve_device()
    if dev.type == "mps":
        if hasattr(torch.mps, "synchronize"):
            try:
                torch.mps.synchronize()
            except Exception:
                pass
    elif dev.type == "cuda":
        if torch.cuda.is_available():
            try:
                torch.cuda.synchronize()
            except Exception:
                pass
