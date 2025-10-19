import logging
import os

from frappe.utils.logger import get_logger

# Initialize logger with error handling for missing directories
try:
    logger = get_logger("zatca", max_size=1_000_000)
    logger.setLevel(logging.INFO)
except (FileNotFoundError, OSError):
    logger = logging.getLogger("zatca")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s zatca %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)


__version__ = "0.55.0"
