 # Copyright (c) 2024, Lavaloon and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock
from result import Ok, Err

from ksa_compliance.test.test_constants import (
    SAUDI_COUNTRY,
    SAUDI_CURRENCY,
    TEST_COMPANY_NAME,
)
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    SalesInvoiceAdditionalFields,
)


class TestSalesInvoiceAdditionalFields(FrappeTestCase):
    customer_name = "Test Customer"
    pos_customer_name = "Test Customer for POS"
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
        
        # Create test customers, item, and POS profile
        self._create_test_customers()
        self._create_test_item()
        self._create_test_pos_profile()

        frappe.logger().info("✅ Test setup completed")

    def tearDown(self):
        """Clean up after each test"""
        frappe.logger().info("🧹 Cleaning up test...")
        # Clean up test data
        if hasattr(self, 'test_sales_invoice') and self.test_sales_invoice:
            try:
                frappe.delete_doc("Sales Invoice", self.test_sales_invoice.name, force=True)
            except:
                pass
        frappe.logger().info("✅ Test cleanup completed")

    def _create_test_customers(self):
        """Create test customers for both Sales Invoice and POS Invoice tests"""
        # Create customer for Sales Invoice tests
        if not frappe.db.exists("Customer", self.customer_name):
            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": self.customer_name,
                "customer_type": "Individual",
                "customer_group": "All Customer Groups",
                "territory": "All Territories",
            })
            customer.insert(ignore_permissions=True)

        # Create customer for POS Invoice tests
        if not frappe.db.exists("Customer", self.pos_customer_name):
            pos_customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": self.pos_customer_name,
                "customer_type": "Individual",
                "customer_group": "All Customer Groups",
                "territory": "All Territories",
            })
            pos_customer.insert(ignore_permissions=True)

    def _create_test_item(self):
        """Create test item for both Sales Invoice and POS Invoice tests"""
        if not frappe.db.exists("Item", self.item_name):
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": self.item_name,
                "item_name": self.item_name,
                "item_group": "Products",
                "is_stock_item": 0,  # Non-stock item to avoid warehouse issues
                "stock_uom": "Nos",
            })
            item.insert(ignore_permissions=True)

    def _create_test_pos_profile(self):
        """Create test POS profile for POS Invoice tests"""
        pos_profile_name = "Test POS Profile"
        if not frappe.db.exists("POS Profile", pos_profile_name):
            pos_profile = frappe.get_doc({
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
                "payments": [{
                    "mode_of_payment": "Cash",
                    "default": 1,
                }],
            })
            pos_profile.insert(ignore_permissions=True)

    def _create_test_sales_invoice(self):
        """Create a test sales invoice for testing"""
        sales_invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": self.customer_name,
            "company": TEST_COMPANY_NAME,
            "currency": SAUDI_CURRENCY,
            "items": [{
                "item_code": self.item_name,
                "qty": 1,
                "rate": 100,
                "amount": 100,
            }],
            "taxes_and_charges": "",
        })
        sales_invoice.insert(ignore_permissions=True)
        sales_invoice.submit()
        
        return sales_invoice

    def _create_test_pos_invoice(self):
        """Create a test POS invoice for testing"""
        pos_invoice = frappe.get_doc({
            "doctype": "POS Invoice",
            "customer": self.pos_customer_name,
            "company": TEST_COMPANY_NAME,
            "currency": SAUDI_CURRENCY,
            "pos_profile": "Test POS Profile",
            "items": [{
                "item_code": self.item_name,
                "qty": 1,
                "rate": 100,
                "amount": 100,
            }],
            "payments": [{
                "mode_of_payment": "Cash",
                "amount": 100,
            }],
            "taxes_and_charges": "",
        })
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
        additional_fields_name = f"{test_sales_invoice.name}-AdditionalFields-1"
        
        # Verify document was created automatically
        self.assertTrue(
            frappe.db.exists("Sales Invoice Additional Fields", additional_fields_name),
            f"Sales Invoice Additional Fields document {additional_fields_name} should be created automatically"
        )
        
        # Get the automatically created document
        additional_fields = frappe.get_doc("Sales Invoice Additional Fields", additional_fields_name)
        
        # Verify fields are set correctly
        self.assertEqual(additional_fields.sales_invoice, test_sales_invoice.name)
        self.assertEqual(additional_fields.invoice_doctype, "Sales Invoice")
        self.assertEqual(additional_fields.tax_currency, SAUDI_CURRENCY)
        
        frappe.logger().info("✅ test_automatic_creation_on_sales_invoice_submit completed successfully")

    def test_automatic_creation_on_pos_invoice_submit(self):
        """Test that Sales Invoice Additional Fields is created automatically when POS Invoice is submitted"""
        frappe.logger().info("🧪 Running test_automatic_creation_on_pos_invoice_submit...")
        
        # Create test POS invoice
        pos_invoice = self._create_test_pos_invoice()
        
        # Check that additional fields document was created automatically
        additional_fields_name = f"{pos_invoice.name}-AdditionalFields-1"
        self.assertTrue(
            frappe.db.exists("Sales Invoice Additional Fields", additional_fields_name),
            f"Additional fields document {additional_fields_name} should be created automatically for POS Invoice"
        )
        
        # Get the automatically created document
        additional_fields = frappe.get_doc("Sales Invoice Additional Fields", additional_fields_name)
        
        # Verify fields are set correctly
        self.assertEqual(additional_fields.sales_invoice, pos_invoice.name)
        self.assertEqual(additional_fields.invoice_doctype, "POS Invoice")
        self.assertEqual(additional_fields.tax_currency, SAUDI_CURRENCY)
        
        # Clean up
        frappe.delete_doc("POS Invoice", pos_invoice.name, force=True)
        
        frappe.logger().info("✅ test_automatic_creation_on_pos_invoice_submit completed successfully")
