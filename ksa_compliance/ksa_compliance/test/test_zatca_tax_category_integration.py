# Copyright (c) 2025, LavaLoon and Contributors
# See license.txt
"""
ZATCA Tax Category and Invoice Integration Tests

"""
import traceback

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from ksa_compliance.ksa_compliance.test.test_invoice_helpers import (
    create_advance_payment_entry,
    create_advance_sales_invoice,
    create_normal_sales_invoice,
    create_sales_tax_template,
    create_tax_category_with_zatca,
    ensure_test_item_exists,
)
from ksa_compliance.test.test_constants import (
    SAUDI_CURRENCY,
    TEST_COMPANY_NAME,
    TEST_TAX_ACCOUNT_NAME,
    TEST_TAX_TEMPLATE_NAME,
)

# Import reusable methods and constants
from ksa_compliance.test.test_setup import _create_customer_address as create_customer_address
from ksa_compliance.test.test_setup import _create_standard_customer as create_standard_customer
from ksa_compliance.test.test_setup import _create_test_item as create_test_item

CUSTOMERS = [
    {
        "name": "Customer-SI-VAT-S1",
        "vat": "311633596400003",
    },  # Advance Sales Invoice test with VAT-S (15%)
    {
        "name": "Customer-SI-VAT-Z1",
        "vat": "311605596400003",
    },  # Advance Sales Invoice test with VAT-Z (0%)
    {
        "name": "Customer-SI-VAT-E1",
        "vat": "311609592200003",
    },  # Advance Sales Invoice test with VAT-E (0%)
    {
        "name": "Customer-PE-VAT-S1",
        "vat": "311609592200004",
    },  # Advance Payment Entry test with VAT-S (15%)
    {
        "name": "Customer-PE-VAT-Z1",
        "vat": "311609592200005",
    },  # Advance Payment Entry test with VAT-Z (0%)
    {
        "name": "Customer-PE-VAT-E1",
        "vat": "311609592200006",
    },  # Advance Payment Entry test with VAT-E (0%)
]

TAX_CATEGORIES = [
    {"name": "CAT-S", "custom_zatca_category": "Standard rate"},
    {"name": "CAT-Z", "custom_zatca_category": "Zero rated goods || Export of goods"},
    {
        "name": "CAT-E",
        "custom_zatca_category": "Exempt from Tax || Real estate transactions mentioned in Article 30 of the VAT Regulations",
    },
]

TAX_TEMPLATES = [
    {"name": "VAT-S", "rate": 15, "category": "CAT-S"},
    {"name": "VAT-Z", "rate": 0, "category": "CAT-Z"},
    {"name": "VAT-E", "rate": 0, "category": "CAT-E"},
]


class TestZATCATaxCategoryIntegration(FrappeTestCase):
    def setUp(self):
        self.company = TEST_COMPANY_NAME
        self.currency = SAUDI_CURRENCY
        self.account_head = f"{TEST_TAX_ACCOUNT_NAME} - {self.company}"
        self.cost_center = f"Main - {self.company}"
        self.debit_to = f"Debtors - {self.company}"
        self.test_item = create_test_item()
        self._create_tax_categories()
        self._create_tax_templates()
        self._create_customers_with_address()

    def _create_tax_categories(self):
        """Create all tax categories with ZATCA mappings."""
        for cat in TAX_CATEGORIES:
            create_tax_category_with_zatca(cat["name"], cat["custom_zatca_category"])

    def _create_tax_templates(self):
        """Create all tax templates."""
        for temp in TAX_TEMPLATES:
            create_sales_tax_template(
                company=self.company,
                template_name=temp["name"],
                tax_rate=temp["rate"],
                tax_category=temp["category"],
            )

    def _create_customers_with_address(self):
        """Create customers with specific tax categories matching their test scenario."""
        # First 3 customers for advance sales invoice tests
        for idx, cust in enumerate(CUSTOMERS[:3]):
            create_standard_customer(
                cust["name"],
                with_address=True,
            )

        # Customers 4-6 for advance payment entry tests
        for idx in range(3, 6):
            create_standard_customer(
                CUSTOMERS[idx]["name"],
                with_address=True,
            )

    def test_tax_category_and_invoice_flow(self):
        """
        Test that invoices can ONLY be settled by advances with MATCHING tax categories.

        For each customer (3 customers):
        1. Create ONE advance payment with a specific tax template (S, Z, or E)
        2. Create 3 normal invoices with different tax templates (S, Z, E)
           - Normal invoices have tax_category EMPTY, only taxes_and_charges is set
        3. Only the invoice with MATCHING tax category should succeed and be settled
        4. Invoices with NON-MATCHING tax categories should NOT be settled

        Total: 9 normal invoices, only 3 should be settled (matching ones)

        Customers:
        - Cas1: Advance with VAT-S, test invoices with S (PASS), Z (FAIL), E (FAIL)
        - Cas2: Advance with VAT-Z, test invoices with S (FAIL), Z (PASS), E (FAIL)
        - Cas3: Advance with VAT-E, test invoices with S (FAIL), Z (FAIL), E (PASS)
        """
        all_templates = ["VAT-S", "VAT-Z", "VAT-E"]

        # Track results for summary
        total_invoices = 0
        settled_invoices = 0
        unsettled_invoices = 0  # Includes both: created but not settled, AND failed to create

        # Test first 3 customers with advance sales invoice
        # Each customer has a specific tax category: Cas1=CAT-S, Cas2=CAT-Z, Cas3=CAT-E
        for idx, cust in enumerate(CUSTOMERS[:3]):
            customer = cust["name"]
            customer_tax_category = TAX_CATEGORIES[idx]["name"]
            advance_template = all_templates[idx]  # This customer's advance payment template

            frappe.logger().info(
                f"\n🧪 Testing Customer {customer} (Tax Category: {customer_tax_category}) "
                f"with advance payment using {advance_template}"
            )

            # STEP 1: Create ONE advance invoice for this customer
            advance_invoice = create_advance_sales_invoice(
                customer=customer, company=self.company, rate=1000, tax_template=advance_template
            )
            self.assertTrue(advance_invoice.name)
            frappe.logger().info(f"   ✅ Created advance invoice: {advance_invoice.name}")

            frappe.db.commit()

            # Verify payment entry was created for the advance
            payment_entries = frappe.get_all(
                "Payment Entry",
                filters={"advance_payment_invoice": advance_invoice.name, "docstatus": 1},
                fields=["name", "paid_amount"],
            )
            self.assertGreater(
                len(payment_entries),
                0,
                f"Payment entry should exist for advance invoice {advance_invoice.name}",
            )

            # STEP 2: Create 3 normal invoices with different tax templates
            # ALL normal invoices have tax_category EMPTY (clear_tax_category=True)

            for template_idx, test_template in enumerate(all_templates):
                should_match = test_template == advance_template
                total_invoices += 1

                if should_match:
                    # Create normal invoice with tax_category EMPTY - should succeed and be settled
                    # Manual advance allocation is handled by the helper method
                    invoice = create_normal_sales_invoice(
                        customer=customer,
                        company=self.company,
                        item_code=self.test_item,
                        item_rate=500,
                        tax_template=test_template,
                        clear_tax_category=True,  # Always clear tax_category for normal invoices
                        submit=True,  # Will submit after allocating advance
                        advance_payment_entry=payment_entries[0].name,  # Manually allocate advance
                    )
                    self.assertTrue(invoice.name)
                    invoice.reload()

                    # Commit to database so you can see it in the site
                    frappe.db.commit()

                    # Verify tax_category is empty on the invoice
                    self.assertEqual(
                        invoice.tax_category or "",
                        "",
                        f"Invoice {invoice.name} should have empty tax_category",
                    )

                    # This invoice should be settled by advance
                    self.assertEqual(
                        flt(invoice.outstanding_amount),
                        0.0,
                        f"Invoice {invoice.name} with {test_template} should be fully settled (outstanding = 0)",
                    )
                    self.assertGreater(
                        len(invoice.advances),
                        0,
                        f"Invoice {invoice.name} should have advances applied",
                    )
                    settled_invoices += 1
                    frappe.logger().info(
                        f"   ✅ PASS: Invoice with {test_template} was settled by advance"
                    )
                else:
                    # NON-MATCHING case: Invoice should FAIL to submit due to tax category mismatch
                    # Create invoice in draft and manually try to allocate non-matching advance
                    # This should raise ValidationError during submit
                    unsettled_invoices += 1

                    with self.assertRaises(frappe.exceptions.ValidationError):
                        # Try to create invoice with non-matching advance - should fail during submit
                        invoice = create_normal_sales_invoice(
                            customer=customer,
                            company=self.company,
                            item_code=self.test_item,
                            item_rate=500,
                            tax_template=test_template,
                            clear_tax_category=True,
                            submit=True,  # This will trigger the ValidationError
                            advance_payment_entry=payment_entries[0].name,  # Non-matching advance
                        )

                    # If we get here, the assertion passed (exception was raised)
                    frappe.logger().info(
                        f"   ✅ PASS: Invoice with {test_template} failed to SUBMIT (non-matching tax category)"
                    )

                    # Rollback the failed transaction
                    frappe.db.rollback()

        frappe.logger().info(
            "\n✅✅✅ All tax category matching/non-matching tests completed successfully ✅✅✅"
        )

    def test_tax_category_with_advance_payment_entry(self):
        """
        Test that invoices can ONLY be settled by advance payment ENTRIES with MATCHING tax categories.

        For each customer (3 customers):
        1. Create ONE advance payment ENTRY with a specific tax template (S, Z, or E)
        2. Create 3 normal invoices with different tax templates (S, Z, E)
           - Normal invoices have tax_category EMPTY, only taxes_and_charges is set
        3. Only the invoice with MATCHING tax category should succeed and be settled
        4. Invoices with NON-MATCHING tax categories should NOT be settled

        Total: 9 normal invoices, only 3 should be settled (matching ones)

        Customers:
        - Customer4: Advance PE with VAT-S, test invoices with S (PASS), Z (FAIL), E (FAIL)
        - Customer5: Advance PE with VAT-Z, test invoices with S (FAIL), Z (PASS), E (FAIL)
        - Customer6: Advance PE with VAT-E, test invoices with S (FAIL), Z (FAIL), E (PASS)
        """
        all_templates = ["VAT-S", "VAT-Z", "VAT-E"]

        # Track results for summary
        total_invoices = 0
        settled_invoices = 0
        unsettled_invoices = 0

        # Test customers 4-6 with advance payment entries
        # Each customer has a specific tax category: C4=VAT-S, C5=VAT-Z, C6=VAT-E
        for idx, cust in enumerate(CUSTOMERS[3:6]):
            customer = cust["name"]
            customer_tax_category = TAX_CATEGORIES[idx]["name"]
            advance_template = all_templates[idx]  # This customer's advance payment entry template

            frappe.logger().info(
                f"\n🧪 Testing Customer {customer} (Tax Category: {customer_tax_category}) "
                f"with advance PAYMENT ENTRY using {advance_template}"
            )

            # STEP 1: Create ONE advance payment ENTRY for this customer
            advance_pe = create_advance_payment_entry(
                customer=customer,
                company=self.company,
                paid_amount=1000,
                tax_template=advance_template,
            )
            self.assertTrue(advance_pe.name)
            frappe.logger().info(f"   ✅ Created advance payment entry: {advance_pe.name}")

            frappe.db.commit()

            # STEP 2: Create 3 normal invoices with different tax templates
            # ALL normal invoices have tax_category EMPTY (clear_tax_category=True)

            for template_idx, test_template in enumerate(all_templates):
                should_match = test_template == advance_template
                total_invoices += 1

                if should_match:
                    # Create normal invoice with tax_category EMPTY - should succeed and be settled
                    # Manual advance allocation is handled by the helper method
                    invoice = create_normal_sales_invoice(
                        customer=customer,
                        company=self.company,
                        item_code=self.test_item,
                        item_rate=500,
                        tax_template=test_template,
                        clear_tax_category=True,  # Always clear tax_category for normal invoices
                        submit=True,  # Will submit after allocating advance
                        advance_payment_entry=advance_pe.name,  # Manually allocate advance
                    )
                    self.assertTrue(invoice.name)
                    invoice.reload()

                    # Commit to database so you can see it in the site
                    frappe.db.commit()

                    # Verify tax_category is empty on the invoice
                    self.assertEqual(
                        invoice.tax_category or "",
                        "",
                        f"Invoice {invoice.name} should have empty tax_category",
                    )

                    # This invoice should be settled by advance payment entry
                    self.assertEqual(
                        flt(invoice.outstanding_amount),
                        0.0,
                        f"Invoice {invoice.name} with {test_template} should be fully settled (outstanding = 0)",
                    )
                    self.assertGreater(
                        len(invoice.advances),
                        0,
                        f"Invoice {invoice.name} should have advances applied",
                    )

                    # Verify the advance is from a Payment Entry
                    for adv in invoice.advances:
                        self.assertEqual(
                            adv.reference_type,
                            "Payment Entry",
                            "Advance should be from Payment Entry",
                        )

                    settled_invoices += 1
                    frappe.logger().info(
                        f"   ✅ PASS: Invoice with {test_template} was settled by advance PE"
                    )
                else:
                    # NON-MATCHING case: Invoice should FAIL to submit due to tax category mismatch
                    # Create invoice in draft and manually try to allocate non-matching advance
                    # This should raise ValidationError during submit
                    unsettled_invoices += 1

                    with self.assertRaises(frappe.exceptions.ValidationError):
                        # Try to create invoice with non-matching advance - should fail during submit
                        invoice = create_normal_sales_invoice(
                            customer=customer,
                            company=self.company,
                            item_code=self.test_item,
                            item_rate=500,
                            tax_template=test_template,
                            clear_tax_category=True,
                            submit=True,  # This will trigger the ValidationError
                            advance_payment_entry=advance_pe.name,  # Non-matching advance
                        )

                    # If we get here, the assertion passed (exception was raised)

                    # Rollback the failed transaction
                    frappe.db.rollback()

        frappe.logger().info(
            "\n✅✅✅ Advance payment ENTRY tax category test completed successfully ✅✅✅"
        )
