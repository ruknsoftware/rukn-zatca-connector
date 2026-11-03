# Copyright (c) 2024, Lavaloon and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return
from frappe import _
from frappe.utils import flt, get_time, get_timedelta, getdate

from ksa_compliance.invoice import InvoiceTypeCode
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    get_xml_summary_values,
)
from ksa_compliance.ksa_compliance.test.ksa_compliance_test_base import KSAComplianceTestBase
from ksa_compliance.patches import _2026_11_02_set_siaf_xml_summary_fields as backfill_patch
from ksa_compliance.utils.xml_parser import parse_xml_to_dict

SUMMARY_FIELDS = (
    "issue_date",
    "issue_time",
    "currency_code",
    "invoice_type_code_label",
    "total_taxes_and_charges",
    "base_total_taxes_and_charges",
)

# Branch links to Company through KSA custom fields. Generating ERPNext test records for it on v16
# loads ERPNext's test bootstrap, which conflicts with the SAR test company.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Branch"]


class TestSalesInvoiceAdditionalFields(KSAComplianceTestBase):
    """Test class for Sales Invoice Additional Fields DocType - inherits from shared test infrastructure"""

    def setUp(self):
        """Set up each test - call parent setup to reuse existing infrastructure"""
        super().setUp()  # Call parent's setUp method to create test data

    def test_basic_setup(self):
        """Test basic test framework setup"""
        frappe.logger().info("🧪 Running test_basic_setup...")

        # Verify test data was created successfully
        self.assertIsNotNone(self.item_name)
        self.assertTrue(frappe.db.exists("Item", self.item_name))
        self.assertTrue(frappe.db.exists("Customer", "standard ZATCA Customer"))
        self.assertTrue(frappe.db.exists("Customer", "simplified ZATCA Customer"))

        frappe.logger().info("✅ test_basic_setup completed successfully")

    def test_automatic_creation_on_sales_invoice_submit(self):
        """Test that Sales Invoice Additional Fields is created automatically when Sales Invoice is submitted"""
        frappe.logger().info("🧪 Running test_automatic_creation_on_sales_invoice_submit...")

        # Create and submit a sales invoice
        test_sales_invoice = self._create_test_sales_invoice()

        # Verify that Sales Invoice Additional Fields was created automatically
        additional_fields = frappe.get_all(
            "Sales Invoice Additional Fields",
            filters={"sales_invoice": test_sales_invoice.name},
            limit=1,
        )

        self.assertTrue(
            len(additional_fields) > 0,
            "Sales Invoice Additional Fields should be created automatically",
        )

        # Get the additional fields document
        additional_fields_doc = frappe.get_doc(
            "Sales Invoice Additional Fields", additional_fields[0].name
        )

        # Verify the relationship
        self.assertEqual(additional_fields_doc.sales_invoice, test_sales_invoice.name)

        frappe.logger().info(
            "✅ test_automatic_creation_on_sales_invoice_submit completed successfully"
        )

    def test_automatic_creation_on_pos_invoice_submit(self):
        """Test that Sales Invoice Additional Fields is created automatically when POS Invoice is submitted"""
        frappe.logger().info("🧪 Running test_automatic_creation_on_pos_invoice_submit...")

        # Create and submit a POS invoice
        pos_invoice = self._create_test_pos_invoice()

        # Verify that Sales Invoice Additional Fields was created automatically
        additional_fields = frappe.get_all(
            "Sales Invoice Additional Fields", filters={"sales_invoice": pos_invoice.name}, limit=1
        )

        self.assertTrue(
            len(additional_fields) > 0,
            "Sales Invoice Additional Fields should be created automatically",
        )

        # Get the additional fields document
        additional_fields_doc = frappe.get_doc(
            "Sales Invoice Additional Fields", additional_fields[0].name
        )

        # Verify the relationship
        self.assertEqual(additional_fields_doc.sales_invoice, pos_invoice.name)

        frappe.logger().info(
            "✅ test_automatic_creation_on_pos_invoice_submit completed successfully"
        )

    def test_summary_fields_match_xml_for_sales_invoice(self):
        """Issue date/time, tax totals and invoice type are filled while the XML is built and match it"""
        sales_invoice = self._create_test_sales_invoice()
        siaf = self._get_latest_siaf(sales_invoice.name)

        self.assertEqual(siaf.issue_date, getdate(sales_invoice.posting_date))
        self.assertEqual(
            get_time(siaf.issue_time).strftime("%H:%M:%S"),
            get_time(sales_invoice.posting_time).strftime("%H:%M:%S"),
        )
        self.assertEqual(siaf.currency_code, sales_invoice.currency)
        self.assertEqual(
            siaf.base_total_taxes_and_charges, flt(sales_invoice.base_total_taxes_and_charges, 2)
        )
        self.assertGreater(siaf.base_total_taxes_and_charges, 0)
        self.assertEqual(siaf.invoice_type_code_label, "Tax Invoice")
        self._assert_summary_fields_match_xml(siaf)

    def test_summary_fields_match_xml_for_credit_note(self):
        """Credit note tax totals are positive, as in the XML, and the type reads Credit Note"""
        sales_invoice = self._create_test_sales_invoice()
        credit_note = make_sales_return(sales_invoice.name)
        credit_note.custom_return_reason = "Testing summary fields"
        # Advance payments left by other tests may be copied from the original invoice; they don't apply here
        credit_note.allocate_advances_automatically = 0
        credit_note.set("advances", [])
        credit_note.insert(ignore_permissions=True)
        credit_note.submit()
        siaf = self._get_latest_siaf(credit_note.name)

        self.assertLess(credit_note.base_total_taxes_and_charges, 0)
        self.assertEqual(
            siaf.base_total_taxes_and_charges,
            abs(flt(credit_note.base_total_taxes_and_charges, 2)),
        )
        self.assertEqual(siaf.invoice_type_code, InvoiceTypeCode.INVOICE_RETURN.value)
        self.assertEqual(siaf.invoice_type_code_label, "Credit Note")
        self._assert_summary_fields_match_xml(siaf)

    def test_backfill_restores_summary_fields_from_xml(self):
        """The backfill patch fills cleared summary fields back from the stored XML"""
        sales_invoice = self._create_test_sales_invoice()
        siaf = self._get_latest_siaf(sales_invoice.name)
        expected = {field: siaf.get(field) for field in SUMMARY_FIELDS}

        frappe.db.set_value(
            siaf.doctype,
            siaf.name,
            # Currency columns are NOT NULL, so clear them to 0
            {field: 0 if "taxes_and_charges" in field else None for field in SUMMARY_FIELDS},
            update_modified=False,
        )
        # Backfill just this record; execute() commits per batch, which would break test rollback
        row = frappe.db.get_value(
            siaf.doctype,
            siaf.name,
            ["name", "invoice_xml", "tax_currency", "invoice_type_code"],
            as_dict=True,
        )
        self.assertTrue(backfill_patch._backfill(row))

        siaf.reload()
        for field in SUMMARY_FIELDS:
            self.assertEqual(siaf.get(field), expected[field], field)

    def test_invoice_type_label_options_match_enum(self):
        """Every InvoiceTypeCode label must be an option of the invoice type Select field"""
        options = frappe.get_meta("Sales Invoice Additional Fields").get_options(
            "invoice_type_code_label"
        )
        self.assertEqual(
            {option for option in options.split("\n") if option},
            {code.label for code in InvoiceTypeCode},
        )

    def test_summary_values_round_tax_to_two_decimals(self):
        """Tax totals are stored with 2 decimals like the XML, whatever the source precision"""
        values = get_xml_summary_values(
            {
                "issue_date": "2026-11-02",
                "invoice_type_code": InvoiceTypeCode.EINVOICE.value,
                "total_taxes_and_charges": 1.2345,
                "base_total_taxes_and_charges": 4.567,
            }
        )
        self.assertEqual(values.total_taxes_and_charges, 1.23)
        self.assertEqual(values.base_total_taxes_and_charges, 4.57)

    def test_summary_values_unknown_invoice_type_code(self):
        """An unknown code leaves the label empty instead of failing"""
        values = get_xml_summary_values({"invoice_type_code": "999"})
        self.assertIsNone(values.invoice_type_code_label)
        self.assertIsNone(values.issue_date)

    def _get_latest_siaf(self, invoice_name: str):
        name = frappe.db.get_value(
            "Sales Invoice Additional Fields", {"sales_invoice": invoice_name, "is_latest": 1}
        )
        self.assertIsNotNone(name, f"No Sales Invoice Additional Fields for {invoice_name}")
        return frappe.get_doc("Sales Invoice Additional Fields", name)

    def _assert_summary_fields_match_xml(self, siaf):
        xml_invoice = parse_xml_to_dict(siaf.get_signed_xml())["invoice"]
        self.assertEqual(siaf.issue_date, getdate(xml_invoice["issue_date"]))
        self.assertEqual(get_timedelta(siaf.issue_time), get_timedelta(xml_invoice["issue_time"]))
        self.assertEqual(siaf.currency_code, xml_invoice["currency_code"])
        self.assertEqual(siaf.invoice_type_code, xml_invoice["invoice_type_code"])
        self.assertEqual(siaf.total_taxes_and_charges, flt(xml_invoice["total_taxes_and_charges"]))
        self.assertEqual(
            siaf.base_total_taxes_and_charges, flt(xml_invoice["base_total_taxes_and_charges"])
        )
