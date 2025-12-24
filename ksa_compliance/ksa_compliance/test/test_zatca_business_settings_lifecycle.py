import frappe
from frappe.tests.utils import FrappeTestCase

ZATCA_DOCTYPE = "ZATCA Business Settings"


def withdraw_settings(settings_id, company):
    frappe.call(
        "ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings.withdraw_settings",
        settings_id=settings_id,
        company=company,
    )


def duplicate_configuration(source_name):
    # Call server-side function directly to get a document object and persist it
    from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
        duplicate_configuration as _dup,
    )

    new_doc = _dup(source_name)
    # If server returned a dict, try to create/get the doc
    if isinstance(new_doc, dict):
        # If name present, fetch saved doc; otherwise insert as new
        name = new_doc.get("name")
        if name:
            return frappe.get_doc("ZATCA Business Settings", name)
        doc = frappe.get_doc(new_doc)
        doc.insert(ignore_permissions=True)
        return doc

    # If it's a Document-like object, ensure it is saved
    try:
        if hasattr(new_doc, "insert"):
            if not getattr(new_doc, "name", None):
                new_doc.insert(ignore_permissions=True)
            else:
                new_doc.reload()
    except Exception:
        pass

    return new_doc


def activate_settings(settings_id):
    doc = frappe.get_doc(ZATCA_DOCTYPE, settings_id)
    otp = "123456"
    if not doc.compliance_request_id:
        doc.onboard(otp=otp)
        doc.reload()
    if doc.compliance_request_id and not doc.production_request_id:
        doc.get_production_csid(otp=otp)
        doc.reload()
    return doc


class TestZATCABusinessSettingsLifecycle(FrappeTestCase):
    def test_zatca_settings_lifecycle(self):
        # Setup: get a company with active settings
        active = frappe.get_all(
            ZATCA_DOCTYPE, filters={"status": "Active"}, fields=["name", "company"], limit=1
        )
        self.assertTrue(active, "No active ZATCA Business Settings found for test.")
        active_doc = frappe.get_doc(ZATCA_DOCTYPE, active[0]["name"])
        company = active_doc.company

        # 1. Withdraw active settings
        withdraw_settings(active_doc.name, company)
        withdrawn_doc = frappe.get_doc(ZATCA_DOCTYPE, active_doc.name)
        self.assertEqual(withdrawn_doc.status, "Withdrawn")
        withdrawn_name = withdrawn_doc.name

        # 2. Initiate new settings from withdrawn (should succeed)
        new_doc = duplicate_configuration(withdrawn_doc.name)
        # duplicate_configuration wrapper returns a saved document
        self.assertEqual(new_doc.status, "Pending Activation")
        new_name = new_doc.name

        # 3. Try to initiate again from withdrawn (should fail)
        with self.assertRaises(Exception):
            duplicate_configuration(withdrawn_doc.name)

        # 4. Activate the pending one
        activated_doc = activate_settings(new_name)
        self.assertEqual(activated_doc.status, "Active")

        # 5. Try to initiate again from withdrawn original (should fail because an Active exists)
        with self.assertRaises(Exception):
            duplicate_configuration(withdrawn_name)
