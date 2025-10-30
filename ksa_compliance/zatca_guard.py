"""
Guard clause helper for ZATCA integration.
This module provides a safe check for ZATCA integration status.
"""

import frappe

from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
    ZATCABusinessSettings,
)


def is_zatca_enabled(company: str | None = None) -> bool:
    """Safely determine if ZATCA integration is enabled for a company."""
    settings = ZATCABusinessSettings.for_company(company)
    return bool(settings and getattr(settings, "enable_zatca_integration", False))
