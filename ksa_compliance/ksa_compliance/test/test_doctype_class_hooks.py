# Copyright (c) 2026, LavaLoon and Contributors
# See license.txt

import frappe

from ksa_compliance import hooks
from ksa_compliance.test.compat import IntegrationTestCase, frappe_major_version

EXPECTED_DOCTYPE_CLASSES = {
    "Payment Reconciliation": "ksa_compliance.standard_doctypes.payment_reconciliation.CustomPaymentReconciliation",
    "Unreconcile Payment": "ksa_compliance.standard_doctypes.unreconcile_payment.CustomUnreconcilePayment",
    "Sales Invoice": "ksa_compliance.standard_doctypes.sales_invoice.AdvanceSalesInvoice",
}


class TestDocTypeClassHooks(IntegrationTestCase):
    def test_doctype_classes_registered_in_one_hook_for_frappe_version(self):
        if frappe_major_version() >= 16:
            active_hook, inactive_hook = "extend_doctype_class", "override_doctype_class"
        else:
            active_hook, inactive_hook = "override_doctype_class", "extend_doctype_class"

        self.assertEqual(getattr(hooks, active_hook, None), EXPECTED_DOCTYPE_CLASSES)
        self.assertFalse(hasattr(hooks, inactive_hook))

    def test_doctype_classes_are_loaded(self):
        for doctype, class_path in EXPECTED_DOCTYPE_CLASSES.items():
            with self.subTest(doctype=doctype):
                self.assertTrue(
                    issubclass(type(frappe.new_doc(doctype)), frappe.get_attr(class_path))
                )
