"""
Guard clause helper for ZATCA integration.
This module provides a safe check for ZATCA integration status.
"""

import frappe
from frappe.utils import cint


def is_zatca_enabled(company: str = None) -> bool:
    """
    Check if ZATCA integration is enabled for a specific company or globally.
    Returns False if the doctype doesn't exist or if integration is disabled.

    Args:
        company: Company name to check ZATCA settings for. If None, checks global settings.

    This prevents errors when:
    - The KSA Compliance Settings doctype hasn't been created yet
    - The app is installed but not configured
    - The integration is explicitly disabled
    - Multiple companies exist with different ZATCA configurations
    """
    if not frappe.db.exists("DocType", "KSA Compliance Settings"):
        return False
    
    global_enabled = cint(frappe.db.get_single_value("KSA Compliance Settings", "enable_zatca_integration"))
    if not global_enabled:
        return False
    
    if not company:
        return global_enabled
    
    if frappe.db.exists("DocType", "ZATCA Business Settings"):
        try:
            from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
            settings = ZATCABusinessSettings.for_company(company)
            return bool(settings and settings.enable_zatca_integration)
        except ImportError:
            pass
    
    return global_enabled
