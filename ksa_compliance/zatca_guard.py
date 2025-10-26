"""
Guard clause helper for ZATCA integration.
This module provides a safe check for ZATCA integration status.
"""

import frappe
from frappe.utils import cint


def is_zatca_enabled() -> bool:
    """
    Check if ZATCA integration is enabled.
    Returns False if the doctype doesn't exist or if integration is disabled.

    This prevents errors when:
    - The KSA Compliance Settings doctype hasn't been created yet
    - The app is installed but not configured
    - The integration is explicitly disabled
    """
    if not frappe.db.exists("DocType", "KSA Compliance Settings"):
        return False
    return cint(frappe.db.get_single_value("KSA Compliance Settings", "enable_zatca_integration"))
