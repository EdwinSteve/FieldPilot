"""Stage `env`: check that the GPU stack is usable before hours of work (README §8.1)."""

import logging
import platform
import sys

log = logging.getLogger(__name__)


def check_environment() -> bool:
    """Log the stack; False when training would not use the GPU."""
    import torch  # noqa: PLC0415 - only the training stages need torch

    log.info("Python %s on %s", sys.version.split()[0], platform.platform())
    log.info("torch %s, CUDA build %s", torch.__version__, torch.version.cuda)
    if not torch.cuda.is_available():
        log.error(
            "CUDA is not available: check the NVIDIA driver (570 or newer for the RTX 50 series)"
        )
        return False
    name = torch.cuda.get_device_name(0)
    major, minor = torch.cuda.get_device_capability(0)
    memory_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    log.info(
        "GPU %s, sm_%d%d, %.1f GB, bf16 %s",
        name,
        major,
        minor,
        memory_gb,
        torch.cuda.is_bf16_supported(),
    )
    x = torch.randn(1024, 1024, device="cuda", dtype=torch.bfloat16)
    torch.cuda.synchronize()
    log.info("bf16 matmul OK: %.3f", float((x @ x).float().abs().mean()))
    return True
