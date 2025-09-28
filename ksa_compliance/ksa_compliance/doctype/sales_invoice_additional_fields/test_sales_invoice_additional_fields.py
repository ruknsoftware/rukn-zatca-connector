# Copyright (c) 2024, Lavaloon and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe import _

from ksa_compliance.ksa_compliance.test.ksa_compliance_test_base import KSAComplianceTestBase


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
            limit=1
        )

        self.assertTrue(len(additional_fields) > 0, "Sales Invoice Additional Fields should be created automatically")

        # Get the additional fields document
        additional_fields_doc = frappe.get_doc("Sales Invoice Additional Fields", additional_fields[0].name)

        # Verify the relationship
        self.assertEqual(additional_fields_doc.sales_invoice, test_sales_invoice.name)

        frappe.logger().info("✅ test_automatic_creation_on_sales_invoice_submit completed successfully")

    def test_automatic_creation_on_pos_invoice_submit(self):
        """Test that Sales Invoice Additional Fields is created automatically when POS Invoice is submitted"""
        frappe.logger().info("🧪 Running test_automatic_creation_on_pos_invoice_submit...")

        # Create and submit a POS invoice
        pos_invoice = self._create_test_pos_invoice()

        # Verify that Sales Invoice Additional Fields was created automatically
        additional_fields = frappe.get_all(
            "Sales Invoice Additional Fields",
            filters={"sales_invoice": pos_invoice.name},
            limit=1
        )

        self.assertTrue(len(additional_fields) > 0, "Sales Invoice Additional Fields should be created automatically")

        # Get the additional fields document
        additional_fields_doc = frappe.get_doc("Sales Invoice Additional Fields", additional_fields[0].name)

        # Verify the relationship
        self.assertEqual(additional_fields_doc.sales_invoice, pos_invoice.name)

        frappe.logger().info("✅ test_automatic_creation_on_pos_invoice_submit completed successfully")