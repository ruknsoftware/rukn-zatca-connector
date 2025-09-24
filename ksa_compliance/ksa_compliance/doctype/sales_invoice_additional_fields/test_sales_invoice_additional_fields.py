# Copyright (c) 2024, Lavaloon and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe import _
from frappe.tests.utils import FrappeTestCase
from result import Err, Ok

from ksa_compliance.test.test_constants import (
    SAUDI_CURRENCY,
    TEST_COMPANY_NAME,
    TEST_POS_NAMING_SERIES,
    TEST_SIMPLIFIED_CUSTOMER_NAME,
    TEST_SINV_NAMING_SERIES,
    TEST_STANDARD_CUSTOMER_NAME,
    TEST_TAX_ACCOUNT_NAME,
    TEST_TAX_CATEGORY_NAME,
    TEST_TAX_TEMPLATE_NAME,
)


class TestSalesInvoiceAdditionalFields(FrappeTestCase):
    item_name = "Test Item"

    @classmethod
    def setUpClass(cls):
        """Set up test class"""
        frappe.logger().info("\n🚀 Starting TestSalesInvoiceAdditionalFields test suite...")
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        """Clean up test class"""
        frappe.logger().info("🏁 TestSalesInvoiceAdditionalFields test suite completed\n")
        super().tearDownClass()

    def setUp(self):
        """Set up each test"""
        frappe.logger().info("🧪 Setting up test...")

        # Create test customers, item, tax template, POS profile, and ZATCA settings
        self._create_test_item()
        self._create_test_pos_profile()
        self._create_test_pos_opening_entry()

        frappe.logger().info("✅ Test setup completed")

    def tearDown(self):
        frappe.logger().info("✅ Test cleanup completed")

    def _create_test_item(self):
        """Create test item for both Sales Invoice and POS Invoice tests"""
        if not frappe.db.exists("Item", self.item_name):
            item = frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": self.item_name,
                    "item_name": self.item_name,
                    "item_group": "Products",
                    "is_stock_item": 0,  # Non-stock item to avoid warehouse issues
                    "stock_uom": "Nos",
                }
            )
            item.insert(ignore_permissions=True)

    def _create_test_pos_profile(self):
        """Create test POS profile for POS Invoice tests"""
        pos_profile_name = "Test POS Profile"
        if not frappe.db.exists("POS Profile", pos_profile_name):
            pos_profile = frappe.get_doc(
                {
                    "doctype": "POS Profile",
                    "name": pos_profile_name,
                    "company": TEST_COMPANY_NAME,
                    "user": "Administrator",
                    "currency": SAUDI_CURRENCY,
                    "warehouse": f"Stores - {TEST_COMPANY_NAME}",
                    "income_account": f"Sales - {TEST_COMPANY_NAME}",
                    "expense_account": f"Cost of Goods Sold - {TEST_COMPANY_NAME}",
                    "cost_center": f"Main - {TEST_COMPANY_NAME}",
                    "write_off_account": f"Write Off - {TEST_COMPANY_NAME}",
                    "write_off_cost_center": f"Main - {TEST_COMPANY_NAME}",
                    "pos_profile_name": pos_profile_name,
                    "payments": [
                        {
                            "mode_of_payment": "Cash",
                            "default": 1,
                        }
                    ],
                }
            )
            pos_profile.insert(ignore_permissions=True)

    def _create_test_pos_opening_entry(self):
        """Create test POS Opening Entry for POS Invoice tests"""
        pos_opening_name = "Test POS Opening Entry"
        if not frappe.db.exists("POS Opening Entry", pos_opening_name):
            pos_opening = frappe.get_doc(
                {
                    "doctype": "POS Opening Entry",
                    "period_start_date": frappe.utils.nowdate(),
                    "posting_date": frappe.utils.nowdate(),
                    "user": "Administrator",
                    "pos_profile": "Test POS Profile",
                    "company": TEST_COMPANY_NAME,
                    "pos_closing_entry": None,
                    "status": "Draft",
                    "docstatus": 0,
                    "balance_details": [
                        {
                            "mode_of_payment": "Cash",
                            "opening_amount": 1000.0,
                        }
                    ],
                }
            )
            pos_opening.insert(ignore_permissions=True)
            pos_opening.submit()

    def _create_test_sales_invoice(self):
        """Create a test sales invoice for testing"""
        tax_template_name = f"{TEST_TAX_TEMPLATE_NAME} - {TEST_COMPANY_NAME}"
        sales_invoice = frappe.new_doc("Sales Invoice")
        sales_invoice.customer = TEST_STANDARD_CUSTOMER_NAME
        sales_invoice.company = TEST_COMPANY_NAME
        sales_invoice.currency = SAUDI_CURRENCY
        sales_invoice.taxes_and_charges = tax_template_name
        sales_invoice.tax_category = TEST_TAX_CATEGORY_NAME

        sales_invoice.naming_series = TEST_SINV_NAMING_SERIES

        sales_invoice.append(
            "items",
            {
                "item_code": self.item_name,
                "qty": 1,
                "rate": 100,
                "income_account": f"Sales - {TEST_COMPANY_NAME}",
                "expense_account": f"Cost of Goods Sold - {TEST_COMPANY_NAME}",
                "cost_center": f"Main - {TEST_COMPANY_NAME}",
            },
        )

        sales_invoice.append(
            "payments",
            {
                "mode_of_payment": "Cash",
                "amount": 100,
            },
        )
        sales_invoice.append(
            "taxes",
            {
                "account_head": f"{TEST_TAX_ACCOUNT_NAME} - {TEST_COMPANY_NAME}",
                "charge_type": "On Net Total",
                "cost_center": f"Main - {TEST_COMPANY_NAME}",
                "description": "VAT 15%",
                "rate": 15.0,
            },
        )
        sales_invoice.insert(ignore_permissions=True)
        sales_invoice.submit()

        return sales_invoice

    def _create_test_pos_invoice(self):
        """Create a test POS invoice for testing"""
        tax_template_name = f"{TEST_TAX_TEMPLATE_NAME} - {TEST_COMPANY_NAME}"
        pos_invoice = frappe.new_doc("POS Invoice")
        pos_invoice.customer = TEST_SIMPLIFIED_CUSTOMER_NAME
        pos_invoice.company = TEST_COMPANY_NAME
        pos_invoice.currency = SAUDI_CURRENCY
        pos_invoice.pos_profile = "Test POS Profile"
        pos_invoice.taxes_and_charges = tax_template_name
        pos_invoice.tax_category = TEST_TAX_CATEGORY_NAME

        pos_invoice.naming_series = TEST_POS_NAMING_SERIES

        pos_invoice.append(
            "items",
            {
                "item_code": self.item_name,
                "qty": 1,
                "rate": 100,
                "income_account": f"Sales - {TEST_COMPANY_NAME}",
                "expense_account": f"Cost of Goods Sold - {TEST_COMPANY_NAME}",
                "cost_center": f"Main - {TEST_COMPANY_NAME}",
            },
        )

        pos_invoice.append(
            "payments",
            {
                "mode_of_payment": "Cash",
                "amount": 115,
            },
        )

        pos_invoice.insert(ignore_permissions=True)
        pos_invoice.submit()

        return pos_invoice

    def test_basic_setup(self):
        """Test basic test framework setup"""
        frappe.logger().info("🧪 Running test_basic_setup...")
        self.assertTrue(True, "Basic test framework is working")
        frappe.logger().info("✅ test_basic_setup completed successfully")

    def test_automatic_creation_on_sales_invoice_submit(self):
        """Test that Sales Invoice Additional Fields is created automatically when Sales Invoice is submitted"""
        frappe.logger().info("🧪 Running test_automatic_creation_on_sales_invoice_submit...")

        # Create test sales invoice
        test_sales_invoice = self._create_test_sales_invoice()

        # Check that additional fields document was created automatically when sales invoice was submitted
        additional_fields_list = frappe.get_all(
            "Sales Invoice Additional Fields", filters={"sales_invoice": test_sales_invoice.name}
        )

        # Verify document was created automatically
        self.assertTrue(
            len(additional_fields_list) > 0,
            f"Sales Invoice Additional Fields document should be created automatically for {test_sales_invoice.name}",
        )

        # Get the automatically created document
        additional_fields_name = additional_fields_list[0].name
        additional_fields = frappe.get_doc(
            "Sales Invoice Additional Fields", additional_fields_name
        )

        # Verify fields are set correctly
        self.assertEqual(additional_fields.sales_invoice, test_sales_invoice.name)
        self.assertEqual(additional_fields.invoice_doctype, "Sales Invoice")
        self.assertEqual(additional_fields.tax_currency, SAUDI_CURRENCY)

        frappe.logger().info(
            "✅ test_automatic_creation_on_sales_invoice_submit completed successfully"
        )

    def test_automatic_creation_on_pos_invoice_submit(self):
        """Test that Sales Invoice Additional Fields is created automatically when POS Invoice is submitted"""
        frappe.logger().info("🧪 Running test_automatic_creation_on_pos_invoice_submit...")

        # Create test POS invoice
        pos_invoice = self._create_test_pos_invoice()

        # Check that additional fields document was created automatically
        additional_fields_list = frappe.get_all(
            "Sales Invoice Additional Fields", filters={"sales_invoice": pos_invoice.name}
        )

        self.assertTrue(
            len(additional_fields_list) > 0,
            f"Additional fields document should be created automatically for POS Invoice {pos_invoice.name}",
        )

        # Get the automatically created document
        additional_fields_name = additional_fields_list[0].name
        additional_fields = frappe.get_doc(
            "Sales Invoice Additional Fields", additional_fields_name
        )

        # Verify fields are set correctly
        self.assertEqual(additional_fields.sales_invoice, pos_invoice.name)
        self.assertEqual(additional_fields.invoice_doctype, "POS Invoice")
        self.assertEqual(additional_fields.tax_currency, SAUDI_CURRENCY)

        frappe.logger().info(
            "✅ test_automatic_creation_on_pos_invoice_submit completed successfully"
        )
