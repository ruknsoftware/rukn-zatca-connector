# Copyright (c) 2024, LavaLoon and Contributors
# See license.txt

"""
ZATCA State 3 Integration Tests
State 3: ZATCA Settings Configured and Enabled
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from ksa_compliance.test.test_constants import (
    SAUDI_COUNTRY,
    SAUDI_CURRENCY,
    TEST_COMPANY_NAME,
    TEST_STANDARD_CUSTOMER_NAME,
    TEST_TAX_ACCOUNT_NAME,
    TEST_TAX_TEMPLATE_NAME,
)


class TestZATCAState3Integration(FrappeTestCase):
    """State 3 Integration Tests: ZATCA Configured and Enabled"""

    def _create_advance_invoice(self, rate=1000):
        """Helper method to create and submit an advance payment invoice."""
        settings_name = f"{TEST_COMPANY_NAME}-{SAUDI_COUNTRY}-{SAUDI_CURRENCY}"
        settings = frappe.get_doc("ZATCA Business Settings", settings_name)
        advance_item = settings.advance_payment_item
        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")
        customer_tax_category = frappe.db.get_value(
            "Customer", TEST_STANDARD_CUSTOMER_NAME, "tax_category"
        )

        advance_invoice = frappe.new_doc("Sales Invoice")
        advance_invoice.customer = TEST_STANDARD_CUSTOMER_NAME
        advance_invoice.company = TEST_COMPANY_NAME
        advance_invoice.currency = SAUDI_CURRENCY
        advance_invoice.posting_date = frappe.utils.nowdate()
        advance_invoice.due_date = frappe.utils.nowdate()
        advance_invoice.debit_to = f"Debtors - {company_abbr}"
        advance_invoice.mode_of_payment = "Cash"
        advance_invoice.tax_category = customer_tax_category
        advance_invoice.taxes_and_charges = f"{TEST_TAX_TEMPLATE_NAME} - {company_abbr}"

        advance_invoice.append(
            "items",
            {
                "item_code": advance_item,
                "qty": 1,
                "rate": rate,
                "income_account": f"Sales - {company_abbr}",
                "cost_center": f"Main - {company_abbr}",
            },
        )

        advance_invoice.append(
            "taxes",
            {
                "charge_type": "On Net Total",
                "account_head": f"{TEST_TAX_ACCOUNT_NAME} - {company_abbr}",
                "cost_center": f"Main - {company_abbr}",
                "description": "VAT 15%",
                "rate": 15.0,
            },
        )

        advance_invoice.insert()
        advance_invoice.submit()

        return advance_invoice

    def test_zatca_sync_is_live(self):
        """
        Ensures that Sync with ZATCA is set to Live in ZATCA Business Settings.
        If not Live, it will change it to Live.
        """
        frappe.logger().info("🧪 Running test_zatca_sync_is_live...")

        # Get ZATCA Business Settings for the company
        settings_name = f"{TEST_COMPANY_NAME}-{SAUDI_COUNTRY}-{SAUDI_CURRENCY}"
        settings = frappe.get_doc("ZATCA Business Settings", settings_name)

        # If not Live, change it to Live
        if settings.sync_with_zatca != "Live":
            frappe.logger().info(
                f"   Changing sync_with_zatca from '{settings.sync_with_zatca}' to 'Live'"
            )
            settings.sync_with_zatca = "Live"
            settings.save()
            frappe.db.commit()

        frappe.logger().info(f"   sync_with_zatca: {settings.sync_with_zatca}")
        frappe.logger().info("✅ test_zatca_sync_is_live completed")

    def test_validate_required_system_settings_enabled(self):
        """
        Confirms that global, account, and ZATCA-specific settings
        (rounding, precision, etc.) are correctly configured.
        """
        frappe.logger().info("🧪 Running test_validate_required_system_settings_enabled...")

        # 1. Check Global Defaults - rounded total should be disabled
        global_defaults = frappe.get_doc("Global Defaults")
        self.assertEqual(
            global_defaults.disable_rounded_total, 1, "Rounded total should be disabled"
        )

        # 2. Check System Settings
        system_settings = frappe.get_doc("System Settings")

        # Float precision should be 2
        self.assertEqual(system_settings.float_precision, "2", "Float precision should be 2")

        # Currency precision should be 2
        self.assertEqual(system_settings.currency_precision, "2", "Currency precision should be 2")

        # Rounding method should be Banker's Rounding
        self.assertEqual(
            system_settings.rounding_method,
            "Banker's Rounding",
            "Rounding method should be Banker's Rounding",
        )

        # 3. Check SAR currency configuration
        sar_currency = frappe.get_doc("Currency", "SAR")
        self.assertEqual(
            flt(sar_currency.smallest_currency_fraction_value),
            0.01,
            "SAR smallest currency fraction should be 0.01",
        )

        frappe.logger().info("✅ test_validate_required_system_settings_enabled completed")

    # =========================================================================
    # Advance Payment Lifecycle Tests
    # =========================================================================

    def test_advance_invoice_creates_payment_entry(self):
        """
        Checks that a submitted advance invoice automatically creates
        a corresponding Payment Entry.
        """
        frappe.logger().info("🧪 Running test_advance_invoice_creates_payment_entry...")

        advance_invoice = self._create_advance_invoice(rate=1000)

        frappe.logger().info(f"   Created advance invoice: {advance_invoice.name}")

        # Check that Payment Entry was created automatically
        payment_entry = frappe.get_all(
            "Payment Entry",
            filters={"advance_payment_invoice": advance_invoice.name, "docstatus": 1},
            fields=["name", "paid_amount", "payment_type"],
        )

        self.assertTrue(
            len(payment_entry) > 0,
            f"Payment Entry should be created for advance invoice {advance_invoice.name}",
        )

        frappe.logger().info(f"   Payment Entry created: {payment_entry[0].name}")
        frappe.logger().info("✅ test_advance_invoice_creates_payment_entry completed")

    def test_advance_invoice_remains_unpaid(self):
        """
        Verifies that the advance invoice remains unpaid (outstanding > 0)
        even after the Payment Entry is created.
        """
        frappe.logger().info("🧪 Running test_advance_invoice_remains_unpaid...")

        advance_invoice = self._create_advance_invoice(rate=1000)

        frappe.logger().info(f"   Created advance invoice: {advance_invoice.name}")
        frappe.logger().info(f"   Grand Total: {advance_invoice.grand_total}")

        # Reload to get updated outstanding_amount after Payment Entry creation
        advance_invoice.reload()

        frappe.logger().info(f"   Outstanding Amount: {advance_invoice.outstanding_amount}")

        # Advance invoice should remain UNPAID (outstanding > 0)
        self.assertGreater(
            advance_invoice.outstanding_amount,
            0,
            f"Advance invoice should remain unpaid but outstanding is {advance_invoice.outstanding_amount}",
        )

        frappe.logger().info("✅ test_advance_invoice_remains_unpaid completed")

    def test_settle_advance_with_auto_apply(self):
        """
        Validates that when 'allocate_advances_automatically' is enabled on ZATCA Business Settings,
        creating a standard sales invoice will automatically settle against available advance payments.

        Steps:
        1. Check that auto-apply is enabled in ZATCA Business Settings
        2. Create an advance payment invoice (creates payment entry with balance for customer)
        3. Create a normal sales invoice with regular items
        4. Verify the invoice outstanding is reduced by the advance payment balance
        """
        frappe.logger().info("🧪 Running test_settle_advance_with_auto_apply...")

        # Step 1: Verify auto-apply advances is enabled in Business Settings
        settings_name = f"{TEST_COMPANY_NAME}-{SAUDI_COUNTRY}-{SAUDI_CURRENCY}"
        settings = frappe.get_doc("ZATCA Business Settings", settings_name)

        frappe.logger().info(
            f"   Checking allocate_advances_automatically: {settings.allocate_advances_automatically}"
        )

        # If not enabled, enable it
        if not settings.allocate_advances_automatically:
            frappe.logger().info("   Enabling allocate_advances_automatically...")
            settings.allocate_advances_automatically = 1
            settings.save()
            frappe.db.commit()

        self.assertEqual(
            settings.allocate_advances_automatically,
            1,
            "allocate_advances_automatically should be enabled in ZATCA Business Settings",
        )

        # Step 2: Create advance payment invoice (1000 SAR + 15% VAT = 1150 SAR available balance)
        advance_invoice = self._create_advance_invoice(rate=1000)
        frappe.logger().info(f"   Created advance invoice: {advance_invoice.name}")
        frappe.logger().info(f"   Advance Grand Total: {advance_invoice.grand_total} SAR")

        # Step 3: Create a standard sales invoice with normal item (500 SAR + 15% VAT = 575 SAR)
        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")
        customer_tax_category = frappe.db.get_value(
            "Customer", TEST_STANDARD_CUSTOMER_NAME, "tax_category"
        )

        # Get a regular item (not the advance payment item)
        test_item = frappe.db.get_value("Item", {"is_stock_item": 0}, "name")
        if not test_item:
            test_item = "Test Item"

        standard_invoice = frappe.new_doc("Sales Invoice")
        standard_invoice.customer = TEST_STANDARD_CUSTOMER_NAME
        standard_invoice.company = TEST_COMPANY_NAME
        standard_invoice.currency = SAUDI_CURRENCY
        standard_invoice.posting_date = frappe.utils.nowdate()
        standard_invoice.due_date = frappe.utils.nowdate()
        standard_invoice.debit_to = f"Debtors - {company_abbr}"
        standard_invoice.tax_category = customer_tax_category
        standard_invoice.taxes_and_charges = f"{TEST_TAX_TEMPLATE_NAME} - {company_abbr}"

        standard_invoice.append(
            "items",
            {
                "item_code": test_item,
                "qty": 1,
                "rate": 500,
                "income_account": f"Sales - {company_abbr}",
                "cost_center": f"Main - {company_abbr}",
            },
        )

        standard_invoice.append(
            "taxes",
            {
                "charge_type": "On Net Total",
                "account_head": f"{TEST_TAX_ACCOUNT_NAME} - {company_abbr}",
                "cost_center": f"Main - {company_abbr}",
                "description": "VAT 15%",
                "rate": 15.0,
            },
        )

        standard_invoice.insert()
        standard_invoice.submit()

        frappe.logger().info(f"   Created standard invoice: {standard_invoice.name}")
        frappe.logger().info(f"   Standard Grand Total: {standard_invoice.grand_total} SAR")

        # Reload to get updated outstanding amount
        standard_invoice.reload()
        frappe.logger().info(f"   Standard Outstanding: {standard_invoice.outstanding_amount} SAR")

        # Step 4: Verify the advance was applied
        # Outstanding should be 0 because:
        # - Invoice total: 575 SAR
        # - Advance available: 1150 SAR
        # - After auto-apply: 575 SAR was used from advance, so outstanding = 0
        self.assertEqual(
            standard_invoice.outstanding_amount,
            0,
            f"Outstanding should be 0 after advance application, but got {standard_invoice.outstanding_amount}",
        )

        frappe.logger().info("✅ test_settle_advance_with_auto_apply completed")
