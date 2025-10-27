"""
Guard clause helper for ZATCA integration.
This module provides a safe check for ZATCA integration status.
"""

import frappe


def is_zatca_enabled(company: str = None) -> bool:
    if frappe.db.exists("DocType", "ZATCA Business Settings"):
        try:
            from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
                ZATCABusinessSettings,
            )

            settings = ZATCABusinessSettings.for_company(company)
            return bool(settings and settings.enable_zatca_integration)
        except ImportError:
            pass
