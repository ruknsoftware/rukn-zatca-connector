# Copyright (c) 2024, LavaLoon and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

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


class KSAComplianceTestBase(FrappeTestCase):
    """Base test class for KSA Compliance tests - provides shared test infrastructure"""

    item_name = "Test Item"

    @classmethod
    def setUpClass(cls):
        """Set up test class - create shared test data"""
        frappe.logger().info("\n🚀 Starting KSA Compliance test suite...")
        # Setup for the entire test class
        cls._create_test_customers()
        cls._create_test_item()
        cls._create_test_tax_template()
        cls._create_test_tax_category()

    @classmethod
    def _create_test_customers(cls):
        """Create test customers"""
        # Create standard customer
        if not frappe.db.exists("Customer", TEST_STANDARD_CUSTOMER_NAME):
            customer = frappe.new_doc("Customer")
            customer.customer_name = TEST_STANDARD_CUSTOMER_NAME
            customer.customer_type = "Individual"
            customer.customer_group = "All Customer Groups"
            customer.territory = "All Territories"
            customer.insert(ignore_permissions=True)

        # Create simplified customer
        if not frappe.db.exists("Customer", TEST_SIMPLIFIED_CUSTOMER_NAME):
            customer = frappe.new_doc("Customer")
            customer.customer_name = TEST_SIMPLIFIED_CUSTOMER_NAME
            customer.customer_type = "Individual"
            customer.customer_group = "All Customer Groups"
            customer.territory = "All Territories"
            customer.insert(ignore_permissions=True)

    @classmethod
    def _create_test_item(cls):
        """Create test item"""
        if not frappe.db.exists("Item", cls.item_name):
            item = frappe.new_doc("Item")
            item.item_code = cls.item_name
            item.item_name = cls.item_name
            item.item_group = "All Item Groups"
            item.is_stock_item = 0  # Non-stock item
            item.insert(ignore_permissions=True)

    @classmethod
    def _create_test_tax_template(cls):
        """Create test tax template"""
        template_name = f"{TEST_TAX_TEMPLATE_NAME} - {TEST_COMPANY_NAME}"
        if not frappe.db.exists("Sales Taxes and Charges Template", template_name):
            template = frappe.new_doc("Sales Taxes and Charges Template")
            template.title = template_name
            template.company = TEST_COMPANY_NAME
            template.is_default = 0
            template.append(
                "taxes",
                {
                    "charge_type": "On Net Total",
                    "account_head": f"{TEST_TAX_ACCOUNT_NAME} - {TEST_COMPANY_NAME}",
                    "description": "VAT 15%",
                    "rate": 15.0,
                    "cost_center": f"Main - {TEST_COMPANY_NAME}",
                },
            )
            template.insert(ignore_permissions=True)

    @classmethod
    def _create_test_tax_category(cls):
        """Create test tax category"""
        if not frappe.db.exists("Tax Category", TEST_TAX_CATEGORY_NAME):
            tax_category = frappe.new_doc("Tax Category")
            tax_category.title = TEST_TAX_CATEGORY_NAME
            tax_category.insert(ignore_permissions=True)

    def setUp(self):
        """Set up each test - create test-specific data"""
        frappe.logger().info("🧪 Setting up test...")
        self._create_test_pos_profile()
        self._create_test_pos_opening_entry()
        frappe.logger().info("✅ Test setup completed")

    def tearDown(self):
        """Clean up after each test"""
        frappe.logger().info("✅ Test cleanup completed")

    def _create_test_pos_profile(self):
        """Create test POS profile"""
        if not frappe.db.exists("POS Profile", "Test POS Profile"):
            pos_profile = frappe.new_doc("POS Profile")
            pos_profile.name = "Test POS Profile"
            pos_profile.pos_profile_name = "Test POS Profile"
            pos_profile.company = TEST_COMPANY_NAME
            pos_profile.currency = SAUDI_CURRENCY
            pos_profile.write_off_account = f"Write Off - {TEST_COMPANY_NAME}"
            pos_profile.write_off_cost_center = f"Main - {TEST_COMPANY_NAME}"
            pos_profile.income_account = f"Sales - {TEST_COMPANY_NAME}"
            pos_profile.expense_account = f"Cost of Goods Sold - {TEST_COMPANY_NAME}"
            pos_profile.cash_bank_account = f"Cash - {TEST_COMPANY_NAME}"
            pos_profile.cost_center = f"Main - {TEST_COMPANY_NAME}"
            pos_profile.warehouse = f"Stores - {TEST_COMPANY_NAME}"
            pos_profile.append(
                "payments",
                {
                    "mode_of_payment": "Cash",
                    "default": 1,
                },
            )
            pos_profile.insert(ignore_permissions=True)

    def _create_test_pos_opening_entry(self):
        """Create test POS opening entry"""
        if not frappe.db.exists("POS Opening Entry", {"pos_profile": "Test POS Profile"}):
            pos_opening = frappe.new_doc("POS Opening Entry")
            pos_opening.period_start_date = frappe.utils.nowdate()
            pos_opening.posting_date = frappe.utils.nowdate()
            pos_opening.pos_profile = "Test POS Profile"
            pos_opening.company = TEST_COMPANY_NAME
            pos_opening.append(
                "balance_details",
                {
                    "mode_of_payment": "Cash",
                    "opening_amount": 1000,
                },
            )
            pos_opening.insert(ignore_permissions=True)
            pos_opening.submit()

    def _create_test_sales_invoice(self, submit=True):
        """Create a test sales invoice for testing"""
        tax_template_name = f"{TEST_TAX_TEMPLATE_NAME} - {TEST_COMPANY_NAME}"
        sales_invoice = frappe.new_doc("Sales Invoice")
        sales_invoice.customer = TEST_STANDARD_CUSTOMER_NAME
        sales_invoice.company = TEST_COMPANY_NAME
        sales_invoice.currency = SAUDI_CURRENCY
        sales_invoice.taxes_and_charges = tax_template_name
        sales_invoice.tax_category = TEST_TAX_CATEGORY_NAME
        sales_invoice.posting_date = frappe.utils.nowdate()
        sales_invoice.posting_time = frappe.utils.nowtime()

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
        sales_invoice.set_taxes()
        sales_invoice.save()
        if submit:
            sales_invoice.submit()
        return sales_invoice

    def _create_test_pos_invoice(self, submit=True):
        """Create a test POS invoice for testing"""
        tax_template_name = f"{TEST_TAX_TEMPLATE_NAME} - {TEST_COMPANY_NAME}"
        pos_invoice = frappe.new_doc("POS Invoice")
        pos_invoice.customer = TEST_SIMPLIFIED_CUSTOMER_NAME
        pos_invoice.company = TEST_COMPANY_NAME
        pos_invoice.currency = SAUDI_CURRENCY
        pos_invoice.pos_profile = "Test POS Profile"
        pos_invoice.taxes_and_charges = tax_template_name
        pos_invoice.tax_category = TEST_TAX_CATEGORY_NAME
        pos_invoice.posting_date = frappe.utils.nowdate()
        pos_invoice.posting_time = frappe.utils.nowtime()

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
                "amount": 100,
            },
        )

        pos_invoice.append(
            "taxes",
            {
                "account_head": f"{TEST_TAX_ACCOUNT_NAME} - {TEST_COMPANY_NAME}",
                "charge_type": "On Net Total",
                "cost_center": f"Main - {TEST_COMPANY_NAME}",
                "description": "VAT 15%",
                "rate": 15.0,
            },
        )

        pos_invoice.insert(ignore_permissions=True)
        pos_invoice.set_taxes()
        pos_invoice.save()
        if submit:
            pos_invoice.submit()
        return pos_invoice
