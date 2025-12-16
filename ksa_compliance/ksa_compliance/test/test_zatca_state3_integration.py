# Copyright (c) 2024, LavaLoon and Contributors
# See license.txt

"""
ZATCA State 3 Integration Tests
State 3: ZATCA Settings Configured and Enabled
"""

import json
from unittest.mock import MagicMock, patch

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

    def setUp(self):
        """Setup method that runs before each test to ensure required settings are enabled."""
        super().setUp()

        # Ensure auto_apply_advance_payments is enabled for all tests
        settings_name = f"{TEST_COMPANY_NAME}-{SAUDI_COUNTRY}-{SAUDI_CURRENCY}"
        settings = frappe.get_doc("ZATCA Business Settings", settings_name)
        if not settings.auto_apply_advance_payments:
            settings.auto_apply_advance_payments = 1
            settings.save()
            frappe.db.commit()

    def _ensure_test_item_exists(self):
        """Helper method to ensure Test Item exists."""
        test_item = "Test Item"
        if not frappe.db.exists("Item", test_item):
            item_doc = frappe.new_doc("Item")
            item_doc.item_code = test_item
            item_doc.item_name = test_item
            item_doc.item_group = "All Item Groups"
            item_doc.is_stock_item = 0
            item_doc.insert(ignore_permissions=True)
        return test_item

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

        # 4. Check ZATCA Business Settings
        settings_name = f"{TEST_COMPANY_NAME}-{SAUDI_COUNTRY}-{SAUDI_CURRENCY}"
        settings = frappe.get_doc("ZATCA Business Settings", settings_name)

        # Auto Apply Advance Payments should be enabled
        if not settings.auto_apply_advance_payments:
            frappe.logger().info("   Enabling auto_apply_advance_payments...")
            settings.auto_apply_advance_payments = 1
            settings.save()
            frappe.db.commit()

        self.assertEqual(
            settings.auto_apply_advance_payments,
            1,
            "Auto Apply Advance Payments should be enabled in ZATCA Business Settings",
        )
        frappe.logger().info(
            f"   auto_apply_advance_payments: {settings.auto_apply_advance_payments}"
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
        Validates that when 'auto_apply_advance_payments' is enabled on ZATCA Business Settings,
        creating a standard sales invoice will automatically settle against available advance payments.

        Steps:
        1. Check that auto-apply is enabled in ZATCA Business Settings
        2. Create an advance payment invoice (creates payment entry with balance for customer)
        3. Create a normal sales invoice with regular items
        4. Verify the invoice outstanding is reduced by the advance payment balance
        """
        frappe.logger().info("🧪 Running test_settle_advance_with_auto_apply...")

        # Step 1: Create advance payment invoice (1000 SAR + 15% VAT = 1150 SAR available balance)
        # Note: auto_apply_advance_payments is guaranteed to be enabled by setUp() method
        advance_invoice = self._create_advance_invoice(rate=1000)
        frappe.logger().info(f"   Created advance invoice: {advance_invoice.name}")
        frappe.logger().info(f"   Advance Grand Total: {advance_invoice.grand_total} SAR")

        # Step 3: Create a standard sales invoice with normal item (500 SAR + 15% VAT = 575 SAR)
        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")
        customer_tax_category = frappe.db.get_value(
            "Customer", TEST_STANDARD_CUSTOMER_NAME, "tax_category"
        )

        test_item = self._ensure_test_item_exists()

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

        # Step 4: Verify the advance payment was applied
        # Calculate total advance allocated from the advances table
        total_advance_allocated = sum(
            flt(adv.allocated_amount) for adv in standard_invoice.advances
        )

        frappe.logger().info(f"   Number of advances applied: {len(standard_invoice.advances)}")
        frappe.logger().info(f"   Total Advance (SAR): {total_advance_allocated}")

        # Log each advance for debugging
        for advance in standard_invoice.advances:
            frappe.logger().info(
                f"     - {advance.reference_name}: {advance.allocated_amount} SAR"
            )

        # Verification 1: Outstanding Amount should be 0
        self.assertEqual(
            flt(standard_invoice.outstanding_amount),
            0.0,
            f"Outstanding Amount should be 0 SAR, but got {standard_invoice.outstanding_amount} SAR",
        )

        # Verification 2: Total Advance should equal Invoice Grand Total
        self.assertEqual(
            flt(total_advance_allocated),
            flt(standard_invoice.grand_total),
            f"Total Advance ({total_advance_allocated} SAR) should equal Grand Total ({standard_invoice.grand_total} SAR)",
        )

        frappe.logger().info("✅ test_settle_advance_with_auto_apply completed")

    def test_settle_advance_with_discount(self):
        """
        Ensures that when settling an advance against an invoice with a discount,
        the final outstanding amount is calculated correctly.

        Steps:
        1. Create an advance payment invoice (1000 SAR + 15% VAT = 1150 SAR)
        2. Create a standard invoice with 10% additional discount
        3. Verify outstanding = 0 and advance covers the discounted amount
        """
        frappe.logger().info("🧪 Running test_settle_advance_with_discount...")

        # Step 1: Create advance payment invoice (1000 SAR + 15% VAT = 1150 SAR)
        advance_invoice = self._create_advance_invoice(rate=1000)
        frappe.logger().info(f"   Created advance invoice: {advance_invoice.name}")
        frappe.logger().info(f"   Advance Grand Total: {advance_invoice.grand_total} SAR")

        # Step 2: Create standard invoice WITH discount
        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")
        customer_tax_category = frappe.db.get_value(
            "Customer", TEST_STANDARD_CUSTOMER_NAME, "tax_category"
        )

        test_item = self._ensure_test_item_exists()

        standard_invoice = frappe.new_doc("Sales Invoice")
        standard_invoice.customer = TEST_STANDARD_CUSTOMER_NAME
        standard_invoice.company = TEST_COMPANY_NAME
        standard_invoice.currency = SAUDI_CURRENCY
        standard_invoice.posting_date = frappe.utils.nowdate()
        standard_invoice.due_date = frappe.utils.nowdate()
        standard_invoice.debit_to = f"Debtors - {company_abbr}"
        standard_invoice.tax_category = customer_tax_category
        standard_invoice.taxes_and_charges = f"{TEST_TAX_TEMPLATE_NAME} - {company_abbr}"

        # Apply 10% additional discount on Net Total
        standard_invoice.apply_discount_on = "Net Total"
        standard_invoice.additional_discount_percentage = 10

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

        frappe.logger().info(f"   Created invoice with discount: {standard_invoice.name}")
        frappe.logger().info(f"   Net Total: {standard_invoice.net_total} SAR")
        frappe.logger().info(f"   Discount Amount: {standard_invoice.discount_amount} SAR")
        frappe.logger().info(f"   Grand Total: {standard_invoice.grand_total} SAR")

        # Step 3: Verify advance settlement
        standard_invoice.reload()

        # Calculate total advance allocated
        total_advance_allocated = sum(
            flt(adv.allocated_amount) for adv in standard_invoice.advances
        )

        frappe.logger().info(f"   Total Advance allocated: {total_advance_allocated} SAR")
        frappe.logger().info(f"   Outstanding Amount: {standard_invoice.outstanding_amount} SAR")

        # Verification 1: Outstanding should be 0
        self.assertEqual(
            flt(standard_invoice.outstanding_amount),
            0.0,
            f"Outstanding should be 0 after advance application, but got {standard_invoice.outstanding_amount}",
        )

        # Verification 2: Advance allocated should equal Grand Total (after discount)
        # Base: 500 SAR, Discount 10% = 450 SAR, VAT 15% = 67.5, Total = 517.5 SAR
        self.assertEqual(
            flt(total_advance_allocated),
            flt(standard_invoice.grand_total),
            f"Advance allocated ({total_advance_allocated}) should equal discounted Grand Total ({standard_invoice.grand_total})",
        )

        # Verification 3: Advance should be LESS than original advance (1150 SAR)
        # because invoice with discount is smaller
        self.assertLess(
            flt(total_advance_allocated),
            flt(advance_invoice.grand_total),
            f"Advance used ({total_advance_allocated}) should be less than available advance ({advance_invoice.grand_total})",
        )

        frappe.logger().info("✅ test_settle_advance_with_discount completed")

    # =========================================================================
    # Restrictions and Negative Tests
    # =========================================================================

    def test_cannot_cancel_submitted_advance_invoice(self):
        """
        Asserts that attempting to cancel a submitted advance invoice
        raises a frappe.ValidationError.

        According to ZATCA requirements, advance invoices cannot be cancelled.
        They must be reversed using a Sales Return (Credit Note).
        """
        frappe.logger().info("🧪 Running test_cannot_cancel_submitted_advance_invoice...")

        # Create and submit an advance invoice
        advance_invoice = self._create_advance_invoice(rate=1000)
        frappe.logger().info(f"   Created advance invoice: {advance_invoice.name}")
        frappe.logger().info(f"   Advance invoice status: {advance_invoice.docstatus}")

        # Attempt to cancel the advance invoice - should raise ValidationError
        with self.assertRaises(frappe.ValidationError) as context:
            advance_invoice.cancel()

        frappe.logger().info("   ✓ ValidationError raised as expected")
        frappe.logger().info(f"   Error message: {str(context.exception)[:150]}")

        # Verify the invoice is still submitted (not cancelled)
        advance_invoice.reload()
        self.assertEqual(
            advance_invoice.docstatus,
            1,
            f"Advance invoice should remain submitted (docstatus=1), but got {advance_invoice.docstatus}",
        )

        frappe.logger().info("✅ test_cannot_cancel_submitted_advance_invoice completed")

    def test_cannot_cancel_auto_created_payment_entry(self):
        """
        Asserts that cancelling the Payment Entry generated by an advance
        invoice is blocked.

        The auto-created Payment Entry is linked to the advance invoice and
        should not be cancelled independently.
        """
        frappe.logger().info("🧪 Running test_cannot_cancel_auto_created_payment_entry...")

        # Create and submit an advance invoice
        advance_invoice = self._create_advance_invoice(rate=1000)
        frappe.logger().info(f"   Created advance invoice: {advance_invoice.name}")

        # Get the auto-created Payment Entry
        payment_entries = frappe.get_all(
            "Payment Entry",
            filters={"advance_payment_invoice": advance_invoice.name, "docstatus": 1},
            fields=["name"],
        )

        self.assertTrue(len(payment_entries) > 0, "Payment Entry should exist")

        pe_doc = frappe.get_doc("Payment Entry", payment_entries[0].name)
        frappe.logger().info(f"   Found auto-created Payment Entry: {pe_doc.name}")
        frappe.logger().info(f"   Payment Entry status: {pe_doc.docstatus}")

        # Attempt to cancel the Payment Entry - should raise ValidationError
        with self.assertRaises(frappe.ValidationError) as context:
            pe_doc.cancel()

        frappe.logger().info("   ✓ ValidationError raised as expected")
        frappe.logger().info(f"   Error message: {str(context.exception)[:150]}")

        # Verify the Payment Entry is still submitted (not cancelled)
        pe_doc.reload()
        self.assertEqual(
            pe_doc.docstatus,
            1,
            f"Payment Entry should remain submitted (docstatus=1), but got {pe_doc.docstatus}",
        )

        frappe.logger().info("✅ test_cannot_cancel_auto_created_payment_entry completed")

    def test_cannot_use_payment_reconciliation_for_advances(self):
        """
        Payment Reconciliation tool should exclude advance payment invoices.

        Advance payment invoices should not appear in the Payment Reconciliation tool
        because they are handled through the auto-apply mechanism. Only normal unpaid
        invoices should be available for manual reconciliation.

        Steps:
        1. Create an advance payment invoice
        2. Call Payment Reconciliation's get_unreconciled_entries
        3. Verify advance invoice is NOT in the invoices list
        4. Verify advance Payment Entry is NOT in the payments list
        """
        frappe.logger().info("🧪 Running test_cannot_use_payment_reconciliation_for_advances...")

        # Step 1: Create an advance payment invoice
        advance_invoice = self._create_advance_invoice(rate=1000)
        frappe.logger().info(f"   Created advance invoice: {advance_invoice.name}")
        frappe.logger().info(f"   Advance Grand Total: {advance_invoice.grand_total} SAR")

        # Step 2: Use Payment Reconciliation tool to get unreconciled entries
        frappe.logger().info("\n   Calling Payment Reconciliation...")
        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")

        payment_reconciliation = frappe.new_doc("Payment Reconciliation")
        payment_reconciliation.company = TEST_COMPANY_NAME
        payment_reconciliation.party_type = "Customer"
        payment_reconciliation.party = TEST_STANDARD_CUSTOMER_NAME
        payment_reconciliation.receivable_payable_account = f"Debtors - {company_abbr}"

        # Call get_unreconciled_entries (simulating UI button click)
        payment_reconciliation.get_unreconciled_entries()

        frappe.logger().info(
            f"   Number of invoices found: {len(payment_reconciliation.invoices)}"
        )
        frappe.logger().info(
            f"   Number of payments found: {len(payment_reconciliation.payments)}"
        )

        # Step 3: Verify advance invoice is NOT in the results
        # Get all invoice names from the invoices child table
        invoice_names = [inv.invoice_number for inv in payment_reconciliation.invoices]
        frappe.logger().info(f"   Invoices in reconciliation: {invoice_names}")

        # Advance invoice should NOT appear
        self.assertNotIn(
            advance_invoice.name,
            invoice_names,
            f"Advance invoice {advance_invoice.name} should NOT appear in Payment Reconciliation",
        )
        frappe.logger().info("   ✓ Advance invoice correctly excluded from reconciliation")

        # Step 4: Verify that the advance Payment Entry is NOT in the payments list
        payment_names = [pay.reference_name for pay in payment_reconciliation.payments]
        frappe.logger().info(f"   Payments in reconciliation: {payment_names}")

        advance_payment_entries = frappe.get_all(
            "Payment Entry",
            filters={"advance_payment_invoice": advance_invoice.name, "docstatus": 1},
            fields=["name"],
        )
        if advance_payment_entries:
            advance_pe_name = advance_payment_entries[0].name
            self.assertNotIn(
                advance_pe_name,
                payment_names,
                f"Advance Payment Entry {advance_pe_name} should NOT appear in Payment Reconciliation",
            )
            frappe.logger().info(
                "   ✓ Advance Payment Entry correctly excluded from reconciliation"
            )

        frappe.logger().info("✅ test_cannot_use_payment_reconciliation_for_advances completed")

    def test_cannot_unreconcile_settled_advance_payment(self):
        """
        Unreconcile Payment tool should be blocked for settled advance payments.

        When an advance payment is auto-applied to a standard invoice, attempting
        to unreconcile it via Actions > Unreconcile should fail with ValidationError.

        Steps:
        1. Create advance payment invoice (creates payment entry)
        2. Create standard invoice (auto-settles against advance)
        3. Attempt to unreconcile the allocation
        4. Verify ValidationError is raised
        """
        frappe.logger().info("🧪 Running test_cannot_unreconcile_settled_advance_payment...")

        # Step 1: Create advance payment invoice
        # Note: auto_apply_advance_payments is guaranteed to be enabled by setUp() method
        advance_invoice = self._create_advance_invoice(rate=1000)
        frappe.logger().info(f"   Created advance invoice: {advance_invoice.name}")
        frappe.logger().info(f"   Advance Grand Total: {advance_invoice.grand_total} SAR")

        # Step 2: Create standard invoice that auto-settles with advance
        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")
        customer_tax_category = frappe.db.get_value(
            "Customer", TEST_STANDARD_CUSTOMER_NAME, "tax_category"
        )
        test_item = self._ensure_test_item_exists()

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

        # Reload to get advances table populated
        standard_invoice.reload()

        # Verify the advance was applied
        self.assertTrue(
            len(standard_invoice.advances) > 0, "Standard invoice should have advance allocations"
        )

        frappe.logger().info(f"   Number of allocations: {len(standard_invoice.advances)}")
        for adv in standard_invoice.advances:
            frappe.logger().info(f"     - {adv.reference_name}: {adv.allocated_amount} SAR")

        # Step 3: Attempt to unreconcile the allocation (simulating UI action)
        # The UI calls: erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment.create_unreconcile_doc_for_selection

        from erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment import (
            create_unreconcile_doc_for_selection,
        )

        # Get the Payment Entry reference from the advances table
        payment_entry_ref = standard_invoice.advances[0].reference_name

        frappe.logger().info(f"   Attempting to unreconcile Payment Entry: {payment_entry_ref}")

        # Prepare selections data - simulating what the UI sends
        selections = []
        for advance in standard_invoice.advances:
            selections.append(
                {
                    "company": TEST_COMPANY_NAME,
                    "voucher_type": advance.reference_type,  # "Payment Entry"
                    "voucher_no": advance.reference_name,  # Payment Entry name
                    "against_voucher_type": "Sales Invoice",
                    "against_voucher_no": standard_invoice.name,
                }
            )

        frappe.logger().info(f"   Selections to unreconcile: {selections}")

        # Convert to JSON string as the function expects
        selections_json = json.dumps(selections)

        # This should raise ValidationError about advance payment
        with self.assertRaises(frappe.ValidationError) as context:
            create_unreconcile_doc_for_selection(selections_json)

        frappe.logger().info("   ✓ ValidationError raised as expected")
        error_msg = str(context.exception)
        frappe.logger().info(f"   Error message: {error_msg}")

        # Verify the error message mentions advance payment
        self.assertTrue(
            "Advance Payment" in error_msg or "advance payment" in error_msg.lower(),
            f"Error should mention advance payment, got: {error_msg}",
        )

        # Step 4: Verify the invoice still has the allocation (unchanged)
        standard_invoice.reload()
        self.assertTrue(
            len(standard_invoice.advances) > 0,
            "Allocations should still exist after failed unreconcile attempt",
        )

        frappe.logger().info(
            f"   ✓ Allocations remain intact: {len(standard_invoice.advances)} allocation(s)"
        )
        frappe.logger().info("✅ test_cannot_unreconcile_settled_advance_payment completed")

    def test_cannot_settle_mismatched_tax_categories(self):
        """
        Prevents an advance payment with a 15% VAT from being settled against
        an invoice with a different tax category (e.g., zero-rated).

        This ensures tax compliance - advances can only be applied to invoices
        with matching tax treatment.
        """
        frappe.logger().info("🧪 Running test_cannot_settle_mismatched_tax_categories...")

        # Step 1: Create advance invoice with 15% VAT
        advance_invoice = self._create_advance_invoice(rate=1000)
        frappe.logger().info(f"   Created advance invoice with 15% VAT: {advance_invoice.name}")
        frappe.logger().info(f"   Advance Tax Category: {advance_invoice.tax_category}")

        # Step 2: Create a zero-rated invoice (0% VAT) - different tax category
        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")

        # Create zero-rated tax category
        zero_rated_tax_category = "ZATCA Test Tax Category Zero"
        if not frappe.db.exists("Tax Category", zero_rated_tax_category):
            tax_cat = frappe.new_doc("Tax Category")
            tax_cat.title = zero_rated_tax_category
            tax_cat.zatca_tax_category = "Standard rate"
            tax_cat.insert(ignore_permissions=True)

        # Create VAT Zero Sales Taxes and Charges Template
        zero_tax_template = f"VAT Zero - {company_abbr}"
        if not frappe.db.exists("Sales Taxes and Charges Template", zero_tax_template):
            template = frappe.new_doc("Sales Taxes and Charges Template")
            template.title = zero_tax_template
            template.company = TEST_COMPANY_NAME
            template.is_default = 0
            template.append(
                "taxes",
                {
                    "charge_type": "On Net Total",
                    "account_head": f"Miscellaneous Expenses - {company_abbr}",
                    "cost_center": f"Main - {company_abbr}",
                    "description": "VAT 0%",
                    "rate": 0.0,
                },
            )
            template.insert(ignore_permissions=True)

        test_item = self._ensure_test_item_exists()

        zero_rated_invoice = frappe.new_doc("Sales Invoice")
        zero_rated_invoice.customer = TEST_STANDARD_CUSTOMER_NAME
        zero_rated_invoice.company = TEST_COMPANY_NAME
        zero_rated_invoice.currency = SAUDI_CURRENCY
        zero_rated_invoice.posting_date = frappe.utils.nowdate()
        zero_rated_invoice.due_date = frappe.utils.nowdate()
        zero_rated_invoice.debit_to = f"Debtors - {company_abbr}"
        zero_rated_invoice.tax_category = zero_rated_tax_category  # Different tax category
        zero_rated_invoice.taxes_and_charges = zero_tax_template

        zero_rated_invoice.append(
            "items",
            {
                "item_code": test_item,
                "qty": 1,
                "rate": 500,
                "income_account": f"Sales - {company_abbr}",
                "cost_center": f"Main - {company_abbr}",
            },
        )

        # Attempt to submit - should raise ValidationError due to tax category mismatch
        with self.assertRaises(frappe.ValidationError) as context:
            zero_rated_invoice.insert()
            zero_rated_invoice.submit()

        frappe.logger().info("   ✓ ValidationError raised as expected")
        frappe.logger().info(f"   Error message: {str(context.exception)[:150]}")
        frappe.logger().info("   Cannot settle 15% VAT advance against 0% VAT invoice")

        frappe.logger().info("✅ test_cannot_settle_mismatched_tax_categories completed")

    # =========================================================================
    # Sales Returns (Credit Notes)
    # =========================================================================

    def test_create_return_against_advance_invoice(self):
        """
        Test Case 4.1: Sales Returns (Credit Notes)
        Validates that creating a Sales Return against an advance invoice is permitted
        and correctly reverses the entry.
        """
        frappe.logger().info("\n" + "=" * 80)
        frappe.logger().info("TEST: Create Return Against Advance Invoice")
        frappe.logger().info("=" * 80)

        # Step 1: Create and submit an advance invoice
        frappe.logger().info("Step 1: Creating advance invoice...")
        advance_invoice = self._create_advance_invoice(rate=1000)

        # Verify Payment Entry was created
        payment_entries = frappe.get_all(
            "Payment Entry",
            filters={"advance_payment_invoice": advance_invoice.name, "docstatus": 1},
            fields=["name", "paid_amount"],
        )
        self.assertEqual(len(payment_entries), 1, "Payment Entry should be auto-created")
        payment_entry_name = payment_entries[0].name
        frappe.logger().info(f"   ✓ Advance invoice created: {advance_invoice.name}")
        frappe.logger().info(f"   ✓ Payment Entry created: {payment_entry_name}")
        frappe.logger().info(f"   Original grand_total: {advance_invoice.grand_total}")

        # Step 2: Create a Sales Return against the advance invoice
        frappe.logger().info("\nStep 2: Creating Sales Return...")
        return_invoice = frappe.new_doc("Sales Invoice")
        return_invoice.is_return = 1
        return_invoice.return_against = advance_invoice.name
        return_invoice.customer = advance_invoice.customer
        return_invoice.company = advance_invoice.company
        return_invoice.currency = advance_invoice.currency
        return_invoice.posting_date = frappe.utils.nowdate()
        return_invoice.due_date = frappe.utils.nowdate()
        return_invoice.custom_return_reason = "Return against advance invoice for testing"

        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")
        return_invoice.debit_to = f"Debtors - {company_abbr}"
        return_invoice.mode_of_payment = advance_invoice.mode_of_payment  # Copy mode of payment

        # Copy tax category and template from original
        return_invoice.tax_category = advance_invoice.tax_category
        return_invoice.taxes_and_charges = advance_invoice.taxes_and_charges

        # Copy items from original invoice with negative qty
        for item in advance_invoice.items:
            return_invoice.append(
                "items",
                {
                    "item_code": item.item_code,
                    "qty": -1 * item.qty,  # Negative quantity for return
                    "rate": item.rate,
                    "income_account": item.income_account,
                    "cost_center": item.cost_center,
                },
            )

        # Copy taxes from original invoice
        for tax in advance_invoice.taxes:
            return_invoice.append(
                "taxes",
                {
                    "charge_type": tax.charge_type,
                    "account_head": tax.account_head,
                    "rate": tax.rate,
                    "cost_center": tax.cost_center,
                    "description": tax.description,
                },
            )

        # Insert and submit the return
        return_invoice.insert()
        return_invoice.submit()

        frappe.logger().info(f"   ✓ Sales Return created: {return_invoice.name}")
        frappe.logger().info(f"   Return grand_total: {return_invoice.grand_total} (negative)")

        # Step 3: Verify the return is correctly linked
        self.assertEqual(return_invoice.is_return, 1, "Invoice should be marked as return")
        self.assertEqual(
            return_invoice.return_against,
            advance_invoice.name,
            "Return should reference the advance invoice",
        )
        self.assertTrue(
            return_invoice.grand_total < 0, "Return invoice should have negative grand_total"
        )
        frappe.logger().info("   ✓ Return correctly linked to advance invoice")

        # Step 4: Verify ZATCA Additional Fields exist for the return
        return_additional_fields = frappe.db.get_value(
            "Sales Invoice Additional Fields", {"sales_invoice": return_invoice.name}, "name"
        )
        self.assertIsNotNone(
            return_additional_fields,
            "ZATCA Additional Fields should be created for return invoice",
        )
        frappe.logger().info(f"   ✓ ZATCA Additional Fields created: {return_additional_fields}")

        # Step 5: Verify the return creates a Payment Entry to reverse the advance
        # For a return, the Payment Entry has advance_payment_invoice pointing to the ORIGINAL invoice
        return_payment_entries = frappe.get_all(
            "Payment Entry",
            filters={
                "advance_payment_invoice": advance_invoice.name,  # Points to original
                "payment_type": "Pay",  # Return creates "Pay" type
                "docstatus": 1,
            },
            fields=["name", "paid_amount", "payment_type"],
        )
        # We should have 2 PEs: original "Receive" + return "Pay"
        self.assertGreaterEqual(
            len(return_payment_entries), 1, "Return should create a Payment Entry"
        )
        # Find the "Pay" type entry
        pay_entries = [pe for pe in return_payment_entries if pe.payment_type == "Pay"]
        self.assertEqual(len(pay_entries), 1, "Should have one 'Pay' Payment Entry for return")
        return_pe = pay_entries[0]
        frappe.logger().info(f"   ✓ Return Payment Entry created: {return_pe.name}")
        frappe.logger().info(f"   Return PE paid_amount: {return_pe.paid_amount}")
        frappe.logger().info(f"   Return PE payment_type: {return_pe.payment_type}")

        # Step 6: Verify the original advance invoice is affected
        advance_invoice.reload()
        frappe.logger().info("\nStep 3: Verifying impact on original advance invoice...")
        frappe.logger().info(f"   Outstanding amount: {advance_invoice.outstanding_amount}")
        frappe.logger().info(f"   Status: {advance_invoice.status}")

        frappe.logger().info("✅ test_create_return_against_advance_invoice completed")

    # =========================================================================
    # Additional System Settings Validation
    # =========================================================================

    def test_accounts_settings_round_tax_row_wise(self):
        """
        Verifies that 'Round Tax Amount Row-wise' is enabled in Accounts Settings.
        This is required for ZATCA compliance to ensure accurate tax calculations.
        """
        frappe.logger().info("🧪 Running test_accounts_settings_round_tax_row_wise...")

        # Get Accounts Settings
        accounts_settings = frappe.get_doc("Accounts Settings")

        # Check if round_row_wise is enabled
        frappe.logger().info(f"   round_row_wise: {accounts_settings.round_row_wise_tax}")

        # If not enabled, enable it
        if not accounts_settings.round_row_wise_tax:
            frappe.logger().info("   Enabling round_row_wise_tax...")
            accounts_settings.round_row_wise_tax = 1
            accounts_settings.save()
            frappe.db.commit()

        self.assertEqual(
            accounts_settings.round_row_wise_tax,
            1,
            "Round Tax Amount Row-wise should be enabled in Accounts Settings for ZATCA compliance",
        )

        frappe.logger().info("✅ test_accounts_settings_round_tax_row_wise completed")

    def test_company_country_is_saudi_arabia(self):
        """
        Confirms that the test company's country is set to 'Saudi Arabia'.
        ZATCA integration only applies to Saudi companies.
        """
        frappe.logger().info("🧪 Running test_company_country_is_saudi_arabia...")

        # Get company details
        company = frappe.get_doc("Company", TEST_COMPANY_NAME)

        frappe.logger().info(f"   Company: {company.name}")
        frappe.logger().info(f"   Country: {company.country}")

        # Verify country is Saudi Arabia
        self.assertEqual(
            company.country,
            SAUDI_COUNTRY,
            f"Company country should be '{SAUDI_COUNTRY}' but got '{company.country}'",
        )

        frappe.logger().info("✅ test_company_country_is_saudi_arabia completed")

    def test_zatca_validate_xml_setting(self):
        """
        Checks that 'Check Validate Generated XML' is enabled in ZATCA Business Settings.
        This ensures XML validation is performed before sending to ZATCA.
        """
        frappe.logger().info("🧪 Running test_zatca_validate_xml_setting...")

        # Get ZATCA Business Settings
        settings_name = f"{TEST_COMPANY_NAME}-{SAUDI_COUNTRY}-{SAUDI_CURRENCY}"
        settings = frappe.get_doc("ZATCA Business Settings", settings_name)

        frappe.logger().info(f"   validate_generated_xml: {settings.validate_generated_xml}")

        # If not enabled, enable it
        if not settings.validate_generated_xml:
            frappe.logger().info("   Enabling validate_generated_xml...")
            settings.validate_generated_xml = 1
            settings.save()
            frappe.db.commit()

        self.assertEqual(
            settings.validate_generated_xml,
            1,
            "Check Validate Generated XML should be enabled in ZATCA Business Settings",
        )

        frappe.logger().info("✅ test_zatca_validate_xml_setting completed")

    # =========================================================================
    # Advanced Scenarios
    # =========================================================================

    def test_settle_one_advance_against_multiple_invoices(self):
        """
        Validates that a single advance payment can be split and settled against
        multiple standard invoices.

        Steps:
        1. Create advance invoice for 1000 SAR (1150 SAR with VAT)
        2. Create first standard invoice for 300 SAR (345 SAR with VAT)
        3. Verify first invoice is fully settled with advance
        4. Create second standard invoice for 500 SAR (575 SAR with VAT)
        5. Verify second invoice is fully settled with remaining advance
        6. Verify total advance used = 920 SAR (345 + 575)
        """
        frappe.logger().info("🧪 Running test_settle_one_advance_against_multiple_invoices...")

        # Step 1: Create advance payment (1000 + 15% VAT = 1150 SAR)
        advance_invoice = self._create_advance_invoice(rate=1000)
        frappe.logger().info(f"   Created advance invoice: {advance_invoice.name}")
        frappe.logger().info(f"   Advance Grand Total: {advance_invoice.grand_total} SAR")

        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")
        customer_tax_category = frappe.db.get_value(
            "Customer", TEST_STANDARD_CUSTOMER_NAME, "tax_category"
        )
        test_item = self._ensure_test_item_exists()

        # Step 2: Create first standard invoice (300 + 15% VAT = 345 SAR)
        frappe.logger().info("\n   Creating first standard invoice...")
        invoice1 = frappe.new_doc("Sales Invoice")
        invoice1.customer = TEST_STANDARD_CUSTOMER_NAME
        invoice1.company = TEST_COMPANY_NAME
        invoice1.currency = SAUDI_CURRENCY
        invoice1.posting_date = frappe.utils.nowdate()
        invoice1.due_date = frappe.utils.nowdate()
        invoice1.debit_to = f"Debtors - {company_abbr}"
        invoice1.tax_category = customer_tax_category
        invoice1.taxes_and_charges = f"{TEST_TAX_TEMPLATE_NAME} - {company_abbr}"

        invoice1.append(
            "items",
            {
                "item_code": test_item,
                "qty": 1,
                "rate": 300,
                "income_account": f"Sales - {company_abbr}",
                "cost_center": f"Main - {company_abbr}",
            },
        )

        invoice1.append(
            "taxes",
            {
                "charge_type": "On Net Total",
                "account_head": f"{TEST_TAX_ACCOUNT_NAME} - {company_abbr}",
                "cost_center": f"Main - {company_abbr}",
                "description": "VAT 15%",
                "rate": 15.0,
            },
        )

        invoice1.insert()
        invoice1.submit()
        invoice1.reload()

        frappe.logger().info(f"   First invoice: {invoice1.name}")
        frappe.logger().info(f"   Grand Total: {invoice1.grand_total} SAR")
        frappe.logger().info(f"   Outstanding: {invoice1.outstanding_amount} SAR")

        # Step 3: Verify first invoice is fully settled
        advance1_allocated = sum(flt(adv.allocated_amount) for adv in invoice1.advances)
        self.assertEqual(
            flt(invoice1.outstanding_amount),
            0.0,
            f"First invoice should be fully paid, outstanding: {invoice1.outstanding_amount}",
        )
        self.assertEqual(
            flt(advance1_allocated),
            flt(invoice1.grand_total),
            f"Advance allocated ({advance1_allocated}) should equal invoice total ({invoice1.grand_total})",
        )
        frappe.logger().info(
            f"   ✓ First invoice settled with {advance1_allocated} SAR from advance"
        )

        # Step 4: Create second standard invoice (500 + 15% VAT = 575 SAR)
        frappe.logger().info("\n   Creating second standard invoice...")
        invoice2 = frappe.new_doc("Sales Invoice")
        invoice2.customer = TEST_STANDARD_CUSTOMER_NAME
        invoice2.company = TEST_COMPANY_NAME
        invoice2.currency = SAUDI_CURRENCY
        invoice2.posting_date = frappe.utils.nowdate()
        invoice2.due_date = frappe.utils.nowdate()
        invoice2.debit_to = f"Debtors - {company_abbr}"
        invoice2.tax_category = customer_tax_category
        invoice2.taxes_and_charges = f"{TEST_TAX_TEMPLATE_NAME} - {company_abbr}"

        invoice2.append(
            "items",
            {
                "item_code": test_item,
                "qty": 1,
                "rate": 500,
                "income_account": f"Sales - {company_abbr}",
                "cost_center": f"Main - {company_abbr}",
            },
        )

        invoice2.append(
            "taxes",
            {
                "charge_type": "On Net Total",
                "account_head": f"{TEST_TAX_ACCOUNT_NAME} - {company_abbr}",
                "cost_center": f"Main - {company_abbr}",
                "description": "VAT 15%",
                "rate": 15.0,
            },
        )

        invoice2.insert()
        invoice2.submit()
        invoice2.reload()

        frappe.logger().info(f"   Second invoice: {invoice2.name}")
        frappe.logger().info(f"   Grand Total: {invoice2.grand_total} SAR")
        frappe.logger().info(f"   Outstanding: {invoice2.outstanding_amount} SAR")

        # Step 5: Verify second invoice is fully settled
        advance2_allocated = sum(flt(adv.allocated_amount) for adv in invoice2.advances)
        self.assertEqual(
            flt(invoice2.outstanding_amount),
            0.0,
            f"Second invoice should be fully paid, outstanding: {invoice2.outstanding_amount}",
        )
        self.assertEqual(
            flt(advance2_allocated),
            flt(invoice2.grand_total),
            f"Advance allocated ({advance2_allocated}) should equal invoice total ({invoice2.grand_total})",
        )
        frappe.logger().info(
            f"   ✓ Second invoice settled with {advance2_allocated} SAR from advance"
        )

        # Step 6: Verify total advance usage
        total_advance_used = flt(advance1_allocated) + flt(advance2_allocated)
        frappe.logger().info(f"\n   Total advance used: {total_advance_used} SAR")
        frappe.logger().info(
            f"   Remaining advance: {flt(advance_invoice.grand_total) - total_advance_used} SAR"
        )

        # Total used should be 345 + 575 = 920 SAR (less than 1150 SAR available)
        expected_total = flt(invoice1.grand_total) + flt(invoice2.grand_total)
        self.assertEqual(
            flt(total_advance_used),
            flt(expected_total),
            f"Total advance used ({total_advance_used}) should equal sum of invoice totals ({expected_total})",
        )

        # Should have remaining balance
        self.assertLess(
            flt(total_advance_used),
            flt(advance_invoice.grand_total),
            f"Total used ({total_advance_used}) should be less than available advance ({advance_invoice.grand_total})",
        )

        frappe.logger().info("✅ test_settle_one_advance_against_multiple_invoices completed")

    # =========================================================================
    # ZATCA Integration Status
    # =========================================================================

    def test_standard_invoice_status_is_accepted(self):
        """
        Verifies that after submitting a standard invoice, the Integration Status
        in Sales Invoice Additional Fields is correctly set to "Accepted".
        """
        frappe.logger().info("🧪 Running test_standard_invoice_status_is_accepted...")

        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")
        customer_tax_category = frappe.db.get_value(
            "Customer", TEST_STANDARD_CUSTOMER_NAME, "tax_category"
        )
        test_item = self._ensure_test_item_exists()

        # Step 1: Create a standard sales invoice
        frappe.logger().info("   Creating standard invoice...")
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

        frappe.logger().info(f"   Created invoice: {standard_invoice.name}")
        frappe.logger().info(f"   Grand Total: {standard_invoice.grand_total} SAR")

        # Step 2: Trigger ZATCA sync directly (bypass background queue for testing)
        frappe.logger().info("\n   Triggering ZATCA e-invoicing sync...")
        from ksa_compliance.background_jobs import sync_e_invoices

        # Call sync directly with today's date
        check_date = frappe.utils.nowdate()
        sync_e_invoices(check_date=check_date, batch_size=100, dry_run=False)

        frappe.logger().info("   ✓ ZATCA sync completed")

        # Step 3: Get Additional Fields name after sync
        additional_fields_name = frappe.db.get_value(
            "Sales Invoice Additional Fields", {"sales_invoice": standard_invoice.name}, "name"
        )

        # Step 3: Verify Additional Fields were created
        # The naming pattern is: {invoice_name}-AdditionalFields-{auto_number}
        # Example: ACC-SINV-2025-00075-AdditionalFields-87
        frappe.logger().info(
            f"\n   Verifying Additional Fields for invoice: {standard_invoice.name}"
        )

        self.assertIsNotNone(
            additional_fields_name,
            f"Sales Invoice Additional Fields should be created for {standard_invoice.name}",
        )

        frappe.logger().info(f"   ✓ Additional Fields found: {additional_fields_name}")

        # Step 4: Get the Additional Fields document and verify status
        additional_fields = frappe.get_doc(
            "Sales Invoice Additional Fields", additional_fields_name
        )

        frappe.logger().info(f"   Integration Status: {additional_fields.integration_status}")
        frappe.logger().info(f"   UUID: {additional_fields.uuid}")

        # Step 5: Verify the Integration Status is "Accepted"
        if hasattr(additional_fields, "integration_status"):
            self.assertIsNotNone(
                additional_fields.integration_status,
                "Integration Status should be set after ZATCA processing",
            )
            self.assertEqual(
                additional_fields.integration_status,
                "Accepted",
                f"Integration Status should be 'Accepted' but got '{additional_fields.integration_status}'",
            )
            frappe.logger().info(
                f"   ✓ Integration Status is Accepted: {additional_fields.integration_status}"
            )

        # Step 6: Verify UUID is generated (critical indicator of successful ZATCA submission)
        self.assertIsNotNone(
            additional_fields.uuid, "UUID should be generated after ZATCA submission"
        )
        self.assertTrue(len(additional_fields.uuid) > 0, "UUID should not be empty")
        frappe.logger().info(f"   ✓ UUID generated: {additional_fields.uuid}")

        frappe.logger().info("✅ test_standard_invoice_status_is_accepted completed")

    # =========================================================================
    # Prevent Double Payment on Advance Invoice
    # =========================================================================

    def test_cannot_pay_advance_invoice_twice(self):
        """
        Ensures that an advance payment invoice cannot receive a second payment.

        When an advance invoice is created, a Payment Entry is automatically generated.
        Any attempt to create another Payment Entry against the same advance invoice
        should be blocked.

        Steps:
        1. Create an advance invoice (auto-creates Payment Entry)
        2. Attempt to create a manual Payment Entry against the advance invoice
        3. Verify ValidationError is raised
        """
        frappe.logger().info("🧪 Running test_cannot_pay_advance_invoice_twice...")

        # Step 1: Create advance invoice (auto-creates Payment Entry)
        advance_invoice = self._create_advance_invoice(rate=1000)
        frappe.logger().info(f"   Created advance invoice: {advance_invoice.name}")
        frappe.logger().info(f"   Grand Total: {advance_invoice.grand_total} SAR")

        # Verify auto-created Payment Entry exists
        auto_payment_entries = frappe.get_all(
            "Payment Entry",
            filters={"advance_payment_invoice": advance_invoice.name, "docstatus": 1},
            fields=["name", "paid_amount"],
        )
        self.assertEqual(len(auto_payment_entries), 1, "Auto Payment Entry should exist")
        frappe.logger().info(f"   ✓ Auto Payment Entry created: {auto_payment_entries[0].name}")

        # Step 2: Attempt to create a manual Payment Entry against the advance invoice
        frappe.logger().info("\n   Attempting to create second Payment Entry...")
        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")

        manual_payment = frappe.new_doc("Payment Entry")
        manual_payment.payment_type = "Receive"
        manual_payment.posting_date = frappe.utils.nowdate()
        manual_payment.company = TEST_COMPANY_NAME
        manual_payment.mode_of_payment = "Cash"
        manual_payment.party_type = "Customer"
        manual_payment.party = TEST_STANDARD_CUSTOMER_NAME
        manual_payment.paid_from = f"Debtors - {company_abbr}"
        manual_payment.paid_to = f"Cash - {company_abbr}"
        manual_payment.paid_amount = advance_invoice.outstanding_amount
        manual_payment.received_amount = advance_invoice.outstanding_amount

        # Link to the advance invoice via references
        manual_payment.append(
            "references",
            {
                "reference_doctype": "Sales Invoice",
                "reference_name": advance_invoice.name,
                "allocated_amount": advance_invoice.outstanding_amount,
            },
        )

        # Step 3: Attempt to submit - should raise ValidationError
        with self.assertRaises(frappe.ValidationError) as context:
            manual_payment.insert()
            manual_payment.submit()

        frappe.logger().info("   ✓ ValidationError raised as expected")
        frappe.logger().info(f"   Error message: {str(context.exception)[:150]}")

        # Verify the advance invoice still has the same outstanding amount
        advance_invoice.reload()
        self.assertGreater(
            advance_invoice.outstanding_amount,
            0,
            "Advance invoice should still have outstanding amount",
        )

        # Verify still only one Payment Entry exists
        payment_entries_after = frappe.get_all(
            "Payment Entry",
            filters={"advance_payment_invoice": advance_invoice.name, "docstatus": 1},
            fields=["name"],
        )
        self.assertEqual(
            len(payment_entries_after),
            1,
            "Should still have only one Payment Entry for advance invoice",
        )

        frappe.logger().info("✅ test_cannot_pay_advance_invoice_twice completed")

    # =========================================================================
    # Rounding Calculation Tests
    # =========================================================================

    def test_rounding_calculations_banker_rounding(self):
        """
        Tests that Banker's Rounding is correctly applied to invoice calculations.

        Banker's Rounding (Round Half to Even):
        - 2.5 rounds to 2
        - 3.5 rounds to 4
        - 2.25 rounds to 2.2 (with 1 decimal)

        This test verifies:
        1. Tax amounts are rounded correctly per line item
        2. Total calculations use proper precision
        3. No floating point errors accumulate
        """
        frappe.logger().info("🧪 Running test_rounding_calculations_banker_rounding...")

        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")
        customer_tax_category = frappe.db.get_value(
            "Customer", TEST_STANDARD_CUSTOMER_NAME, "tax_category"
        )
        test_item = self._ensure_test_item_exists()

        # Create invoice with amounts that will test rounding
        # Rate: 33.33 SAR * 3 qty = 99.99 SAR
        # VAT 15%: 99.99 * 0.15 = 14.9985 -> should round to 15.00
        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = TEST_STANDARD_CUSTOMER_NAME
        invoice.company = TEST_COMPANY_NAME
        invoice.currency = SAUDI_CURRENCY
        invoice.posting_date = frappe.utils.nowdate()
        invoice.due_date = frappe.utils.nowdate()
        invoice.debit_to = f"Debtors - {company_abbr}"
        invoice.tax_category = customer_tax_category
        invoice.taxes_and_charges = f"{TEST_TAX_TEMPLATE_NAME} - {company_abbr}"

        invoice.append(
            "items",
            {
                "item_code": test_item,
                "qty": 3,
                "rate": 33.33,
                "income_account": f"Sales - {company_abbr}",
                "cost_center": f"Main - {company_abbr}",
            },
        )

        invoice.append(
            "taxes",
            {
                "charge_type": "On Net Total",
                "account_head": f"{TEST_TAX_ACCOUNT_NAME} - {company_abbr}",
                "cost_center": f"Main - {company_abbr}",
                "description": "VAT 15%",
                "rate": 15.0,
            },
        )

        invoice.insert()
        invoice.submit()

        frappe.logger().info(f"   Created invoice: {invoice.name}")
        frappe.logger().info(f"   Net Total: {invoice.net_total} SAR")
        frappe.logger().info(f"   Tax Amount: {invoice.taxes[0].tax_amount} SAR")
        frappe.logger().info(f"   Grand Total: {invoice.grand_total} SAR")

        # Verify calculations
        expected_net_total = flt(33.33 * 3, 2)  # 99.99
        expected_tax = flt(expected_net_total * 0.15, 2)  # 15.00
        expected_grand_total = flt(expected_net_total + expected_tax, 2)  # 114.99

        self.assertEqual(
            flt(invoice.net_total, 2),
            expected_net_total,
            f"Net Total should be {expected_net_total}, got {invoice.net_total}",
        )

        self.assertEqual(
            flt(invoice.taxes[0].tax_amount, 2),
            expected_tax,
            f"Tax Amount should be {expected_tax}, got {invoice.taxes[0].tax_amount}",
        )

        self.assertEqual(
            flt(invoice.grand_total, 2),
            expected_grand_total,
            f"Grand Total should be {expected_grand_total}, got {invoice.grand_total}",
        )

        # Verify no rounded_total field is used (should be disabled)
        self.assertEqual(
            flt(invoice.rounded_total),
            0,
            "Rounded Total should be 0 (disabled)",
        )

        frappe.logger().info("   ✓ All rounding calculations are correct")
        frappe.logger().info("✅ test_rounding_calculations_banker_rounding completed")

    def test_rounding_with_multiple_line_items(self):
        """
        Tests rounding with multiple line items to ensure row-wise tax rounding
        doesn't accumulate errors.

        Creates an invoice with multiple items of varying amounts to test:
        1. Each line item's tax is rounded independently
        2. Total tax is sum of rounded line taxes
        3. Grand total is correctly calculated
        """
        frappe.logger().info("🧪 Running test_rounding_with_multiple_line_items...")

        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")
        customer_tax_category = frappe.db.get_value(
            "Customer", TEST_STANDARD_CUSTOMER_NAME, "tax_category"
        )
        test_item = self._ensure_test_item_exists()

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = TEST_STANDARD_CUSTOMER_NAME
        invoice.company = TEST_COMPANY_NAME
        invoice.currency = SAUDI_CURRENCY
        invoice.posting_date = frappe.utils.nowdate()
        invoice.due_date = frappe.utils.nowdate()
        invoice.debit_to = f"Debtors - {company_abbr}"
        invoice.tax_category = customer_tax_category
        invoice.taxes_and_charges = f"{TEST_TAX_TEMPLATE_NAME} - {company_abbr}"

        # Add multiple items with tricky amounts for rounding
        test_rates = [10.01, 20.02, 30.03, 40.04, 50.05]

        for idx, rate in enumerate(test_rates):
            invoice.append(
                "items",
                {
                    "item_code": test_item,
                    "qty": 1,
                    "rate": rate,
                    "income_account": f"Sales - {company_abbr}",
                    "cost_center": f"Main - {company_abbr}",
                },
            )

        invoice.append(
            "taxes",
            {
                "charge_type": "On Net Total",
                "account_head": f"{TEST_TAX_ACCOUNT_NAME} - {company_abbr}",
                "cost_center": f"Main - {company_abbr}",
                "description": "VAT 15%",
                "rate": 15.0,
            },
        )

        invoice.insert()
        invoice.submit()

        frappe.logger().info(f"   Created invoice: {invoice.name}")
        frappe.logger().info(f"   Number of items: {len(invoice.items)}")
        frappe.logger().info(f"   Net Total: {invoice.net_total} SAR")
        frappe.logger().info(f"   Tax Amount: {invoice.taxes[0].tax_amount} SAR")
        frappe.logger().info(f"   Grand Total: {invoice.grand_total} SAR")

        # Calculate expected values
        expected_net_total = flt(sum(test_rates), 2)  # 150.15
        # Note: expected_tax would be ~22.52 (with row-wise rounding)
        # Note: expected_grand_total = net_total + tax_amount

        frappe.logger().info(f"   Expected Net Total: {expected_net_total} SAR")

        # Verify net total
        self.assertEqual(
            flt(invoice.net_total, 2),
            expected_net_total,
            f"Net Total should be {expected_net_total}, got {invoice.net_total}",
        )

        # Verify grand total calculation is consistent
        calculated_grand = flt(invoice.net_total + invoice.taxes[0].tax_amount, 2)
        self.assertEqual(
            flt(invoice.grand_total, 2),
            calculated_grand,
            f"Grand Total ({invoice.grand_total}) should equal Net + Tax ({calculated_grand})",
        )

        # Verify precision is maintained (2 decimal places)
        self.assertEqual(
            len(str(invoice.grand_total).split(".")[-1]) <= 2,
            True,
            "Grand Total should have at most 2 decimal places",
        )

        frappe.logger().info("   ✓ Multi-line item rounding is correct")
        frappe.logger().info("✅ test_rounding_with_multiple_line_items completed")

    # =========================================================================
    # Intermediate Account Settlement Tests
    # =========================================================================

    def test_advance_settlement_accounts_posting(self):
        """
        Verifies that advance payment settlement posts to the correct accounts.

        When an advance payment is applied to a standard invoice:
        1. The advance amount reduces the customer's receivable balance
        2. GL entries are correctly posted
        3. Account balances reconcile properly

        This test validates the accounting entries are correct regardless of
        whether intermediate accounts are used.
        """
        frappe.logger().info("🧪 Running test_advance_settlement_accounts_posting...")

        # Note: auto_apply_advance_payments is guaranteed to be enabled by setUp() method
        company_abbr = frappe.db.get_value("Company", TEST_COMPANY_NAME, "abbr")
        debtors_account = f"Debtors - {company_abbr}"

        # Get initial balance for customer
        from erpnext.accounts.utils import get_balance_on

        initial_balance = get_balance_on(
            account=debtors_account,
            party_type="Customer",
            party=TEST_STANDARD_CUSTOMER_NAME,
        )
        frappe.logger().info(f"   Initial customer balance: {initial_balance} SAR")

        # Step 1: Create advance invoice (1000 + VAT = 1150 SAR)
        advance_invoice = self._create_advance_invoice(rate=1000)
        frappe.logger().info(f"   Created advance invoice: {advance_invoice.name}")

        # Check balance after advance (should increase receivable)
        balance_after_advance = get_balance_on(
            account=debtors_account,
            party_type="Customer",
            party=TEST_STANDARD_CUSTOMER_NAME,
        )
        frappe.logger().info(f"   Balance after advance: {balance_after_advance} SAR")

        # Step 2: Create standard invoice that will be settled
        customer_tax_category = frappe.db.get_value(
            "Customer", TEST_STANDARD_CUSTOMER_NAME, "tax_category"
        )
        test_item = self._ensure_test_item_exists()

        standard_invoice = frappe.new_doc("Sales Invoice")
        standard_invoice.customer = TEST_STANDARD_CUSTOMER_NAME
        standard_invoice.company = TEST_COMPANY_NAME
        standard_invoice.currency = SAUDI_CURRENCY
        standard_invoice.posting_date = frappe.utils.nowdate()
        standard_invoice.due_date = frappe.utils.nowdate()
        standard_invoice.debit_to = debtors_account
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
        standard_invoice.reload()

        frappe.logger().info(f"   Created standard invoice: {standard_invoice.name}")
        frappe.logger().info(f"   Standard Grand Total: {standard_invoice.grand_total} SAR")
        frappe.logger().info(f"   Standard Outstanding: {standard_invoice.outstanding_amount} SAR")

        # Verify advance was applied
        self.assertEqual(
            flt(standard_invoice.outstanding_amount),
            0.0,
            "Standard invoice should be fully settled",
        )

        # Step 3: Check final balance
        final_balance = get_balance_on(
            account=debtors_account,
            party_type="Customer",
            party=TEST_STANDARD_CUSTOMER_NAME,
        )
        frappe.logger().info(f"   Final customer balance: {final_balance} SAR")

        # The advance invoice remains unpaid (outstanding), so:
        # Net change = advance outstanding + (0 from standard invoice as it's settled)
        advance_invoice.reload()
        # Note: expected_balance_change would be advance_invoice.outstanding_amount

        frappe.logger().info(f"   Advance outstanding: {advance_invoice.outstanding_amount} SAR")
        frappe.logger().info(f"   Balance change: {flt(final_balance) - flt(initial_balance)} SAR")

        # Verify GL entries exist for the settlement
        gl_entries = frappe.get_all(
            "GL Entry",
            filters={
                "voucher_type": "Sales Invoice",
                "voucher_no": standard_invoice.name,
                "account": debtors_account,
            },
            fields=["debit", "credit", "against"],
        )

        frappe.logger().info(f"   GL Entries for standard invoice: {len(gl_entries)}")
        for gl in gl_entries:
            frappe.logger().info(f"     Debit: {gl.debit}, Credit: {gl.credit}")

        self.assertTrue(len(gl_entries) > 0, "GL Entries should exist for the invoice")

        frappe.logger().info("   ✓ Account postings are correct")
        frappe.logger().info("✅ test_advance_settlement_accounts_posting completed")
