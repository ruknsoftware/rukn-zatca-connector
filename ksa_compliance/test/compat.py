"""
Test helpers that work on both Frappe v15 and v16+.
"""

import frappe

try:
    from frappe.tests import IntegrationTestCase
except ImportError:  # Frappe v15 and older
    from frappe.tests.utils import FrappeTestCase as IntegrationTestCase

__all__ = ["IntegrationTestCase", "frappe_major_version"]


def frappe_major_version() -> int:
    return int(frappe.__version__.split(".")[0])
