"""
Guard clause helper for ZATCA integration.
This module provides a safe check for ZATCA integration status.
"""

import frappe


def is_zatca_enabled(company: str | None = None) -> bool:
    """Safely determine if ZATCA integration is enabled for a company.

    Defensive defaults:
    - If the DocType or settings aren't available, return False.
    - If company is None, treat as disabled (tests and non-ZATCA flows should pass).
    - Never raise from here; this is a guard used widely across hooks.
    """
    try:
        if not company:
            return False
        try:
            from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
                ZATCABusinessSettings,
            )
        except Exception:
            return False

        settings = ZATCABusinessSettings.for_company(company)
        return bool(settings and getattr(settings, "enable_zatca_integration", False))
    except Exception:
        return False
