import os
import sys
from typing import Any

import psutil
from loguru import logger as loguru_logger


def setup_logging(log_level: str | None = None):
    """Return a project-wide Loguru logger."""

    log_level = log_level or os.getenv("LOG_LEVEL", "DEBUG").upper()

    loguru_logger.remove()
    loguru_logger.add(
        sys.stdout,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan> - "
        "<level>{message}</level>",
    )
    loguru_logger.debug(f"Logging initialized at {log_level} level (Loguru).")
    return loguru_logger


def log_batch_status(
    logger: Any,
    action: str,
    batch_size: int,
    total_articles: int | None = None,
    total_chunks: int | None = None,
    context: str = "",
) -> str:
    """Log batch action details along with current process and system memory usage."""

    process = psutil.Process()
    mem = process.memory_info()
    rss_mb = mem.rss / 1024 / 1024
    vms_mb = mem.vms / 1024 / 1024

    svmem = psutil.virtual_memory()
    sys_used_mb = svmem.used / 1024 / 1024
    sys_percent = svmem.percent

    details = (
        f"{action} | batch_size={batch_size}"
        f"{f', total_articles={total_articles}' if total_articles is not None else ''}"
        f"{f', total_chunks={total_chunks}' if total_chunks is not None else ''}"
        f"{f', context={context}' if context else ''}"
        f" | process_mem: RSS={rss_mb:.1f}MB, VMS={vms_mb:.1f}MB"
        f" | system_mem: used={sys_used_mb:.1f}MB ({sys_percent:.0f}%)"
    )
    logger.info(details)
    return details
