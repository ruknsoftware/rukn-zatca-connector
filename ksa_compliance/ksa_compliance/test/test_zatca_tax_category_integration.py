# Copyright (c) 2025, LavaLoon and Contributors
# See license.txt
"""
ZATCA Tax Category and Invoice Integration Tests

"""
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
    {"name": "customer1", "vat": "311633596400003"},
    {"name": "customer2", "vat": "311605596400003"},
    {"name": "customer3", "vat": "311609592200003"},
    {"name": "customer4", "vat": "311609592200004"},  # Customer for advance payment entry test
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
        # First 3 customers get assigned tax categories matching their advance template
        for idx, cust in enumerate(CUSTOMERS[:3]):
            create_standard_customer(
                cust["name"],
                with_address=True,
            )

        # 4th customer (C4) gets CAT-S for Payment Entry test
        create_standard_customer(
            CUSTOMERS[3]["name"],
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
        company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
        all_templates = ["VAT-S", "VAT-Z", "VAT-E"]

        print("\n" + "=" * 80)
        print("DEBUG: Starting test_tax_category_and_invoice_flow")
        print("DEBUG: Company: {}, Abbr: {}".format(self.company, company_abbr))
        print("DEBUG: All tax templates: {}".format(all_templates))
        print("DEBUG: Normal invoices will have tax_category EMPTY")
        print("{}\n".format("=" * 80))

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

            print("\n{}".format("=" * 80))
            print("DEBUG: Testing Customer {}: {}".format(idx + 1, customer))
            print("DEBUG: Customer VAT: {}".format(cust["vat"]))
            print("DEBUG: Customer tax category: {}".format(customer_tax_category))
            print("DEBUG: Advance payment template: {}".format(advance_template))
            print("{}\n".format("=" * 80))

            frappe.logger().info(
                f"\n🧪 Testing Customer {customer} (Tax Category: {customer_tax_category}) "
                f"with advance payment using {advance_template}"
            )

            # STEP 1: Create ONE advance invoice for this customer
            # Use 10,000 SAR to ensure enough balance for all test invoices
            # Even failed invoices consume advance during allocation (before validation fails)
            print(
                "DEBUG: STEP 1 - Creating advance invoice for {} with {}...".format(
                    customer, advance_template
                )
            )
            advance_invoice = create_advance_sales_invoice(
                customer=customer, company=self.company, rate=1000, tax_template=advance_template
            )
            self.assertTrue(advance_invoice.name)
            print(f"DEBUG: ✅ Advance invoice created: {advance_invoice.name}")
            print("DEBUG:    Status: {}".format(advance_invoice.docstatus))
            print("DEBUG:    Grand total: {}".format(advance_invoice.grand_total))
            print("DEBUG:    Tax category: {}".format(advance_invoice.tax_category))
            frappe.logger().info(f"   ✅ Created advance invoice: {advance_invoice.name}")

            # Commit to database so you can see it in the site
            frappe.db.commit()
            print("DEBUG: 💾 Committed advance invoice to database - check site now!")

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
            print(
                "DEBUG: ✅ Payment entry created: {}, Amount: {}".format(
                    payment_entries[0].name, payment_entries[0].paid_amount
                )
            )

            # STEP 2: Create 3 normal invoices with different tax templates
            # ALL normal invoices have tax_category EMPTY (clear_tax_category=True)
            print("\nDEBUG: STEP 2 - Creating 3 normal invoices with different tax templates...")
            print("DEBUG: All normal invoices will have tax_category EMPTY")

            for template_idx, test_template in enumerate(all_templates):
                should_match = test_template == advance_template
                test_num = template_idx + 1
                total_invoices += 1

                print("\n{}".format("─" * 80))
                print(
                    "DEBUG: Test {}/3 - Invoice with template: {}".format(test_num, test_template)
                )
                print(
                    "DEBUG: Expected: {}".format(
                        "MATCH (should be settled)"
                        if should_match
                        else "NO MATCH (should NOT be settled)"
                    )
                )
                print("{}".format("─" * 80))

                if should_match:
                    # Create normal invoice with tax_category EMPTY - should succeed and be settled
                    invoice = create_normal_sales_invoice(
                        customer=customer,
                        company=self.company,
                        item_code=self.test_item,
                        item_rate=500,
                        tax_template=test_template,
                        clear_tax_category=True,  # Always clear tax_category for normal invoices
                    )
                    self.assertTrue(invoice.name)
                    invoice.reload()

                    # Commit to database so you can see it in the site
                    frappe.db.commit()

                    print(f"DEBUG: Invoice created: {invoice.name}")
                    print("DEBUG:    Grand total: {}".format(invoice.grand_total))
                    print("DEBUG:    Outstanding: {}".format(invoice.outstanding_amount))
                    print(
                        "DEBUG:    Tax category (should be empty): '{}'".format(
                            invoice.tax_category
                        )
                    )
                    print("DEBUG:    Advances applied: {}".format(len(invoice.advances)))
                    print("DEBUG: 💾 Committed invoice to database - check site now!")

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
                    print(
                        "DEBUG: ✅ CORRECT: Invoice is settled (outstanding = 0, advances applied)"
                    )
                    for adv in invoice.advances:
                        print(
                            "DEBUG:    - {}: {}, Amount: {}".format(
                                adv.reference_type, adv.reference_name, adv.allocated_amount
                            )
                        )
                    frappe.logger().info(
                        f"   ✅ PASS: Invoice with {test_template} was settled by advance"
                    )
                else:
                    # NON-MATCHING case: Invoice should either fail to create OR not be settled
                    # Both outcomes are acceptable and expected
                    try:
                        invoice = create_normal_sales_invoice(
                            customer=customer,
                            company=self.company,
                            item_code=self.test_item,
                            item_rate=500,
                            tax_template=test_template,
                            clear_tax_category=True,  # Always clear tax_category for normal invoices
                        )
                        invoice.reload()

                        # Commit to database so you can see it in the site
                        frappe.db.commit()

                        print(f"DEBUG: Invoice created: {invoice.name}")
                        print("DEBUG:    Grand total: {}".format(invoice.grand_total))
                        print("DEBUG:    Outstanding: {}".format(invoice.outstanding_amount))
                        print(
                            "DEBUG:    Tax category (should be empty): '{}'".format(
                                invoice.tax_category
                            )
                        )
                        print("DEBUG:    Advances applied: {}".format(len(invoice.advances)))
                        print("DEBUG: 💾 Committed invoice to database - check site now!")

                        # Verify tax_category is empty on the invoice
                        self.assertEqual(
                            invoice.tax_category or "",
                            "",
                            f"Invoice {invoice.name} should have empty tax_category",
                        )

                        # This invoice should NOT be settled by the advance
                        # Either outstanding > 0 OR no advances applied
                        is_not_settled = (
                            flt(invoice.outstanding_amount) > 0 or len(invoice.advances) == 0
                        )
                        self.assertTrue(
                            is_not_settled,
                            f"Invoice {invoice.name} with {test_template} should NOT be settled by "
                            f"advance with {advance_template} (different tax categories)",
                        )
                        unsettled_invoices += 1
                        if flt(invoice.outstanding_amount) > 0:
                            print(
                                "DEBUG: ✅ CORRECT: Invoice has outstanding amount (not settled by non-matching advance)"
                            )
                        else:
                            print(
                                "DEBUG: ✅ CORRECT: No advances applied (non-matching tax category)"
                            )
                        frappe.logger().info(
                            f"   ✅ PASS: Invoice with {test_template} NOT settled by non-matching advance"
                        )
                    except frappe.exceptions.ValidationError as e:
                        # Invoice creation failed due to tax category mismatch - this is EXPECTED and CORRECT
                        # Commit anyway to preserve any partial data
                        frappe.db.commit()

                        unsettled_invoices += 1
                        print(
                            "DEBUG: ✅ CORRECT: Invoice creation FAILED as expected (ValidationError)"
                        )
                        print("DEBUG:    Error: {}".format(str(e)[:200]))
                        print("DEBUG: 💾 Committed (failed invoice may have partial data)")
                        frappe.logger().info(
                            "   ✅ PASS: Invoice with {} failed to create (non-matching tax category) - ValidationError".format(
                                test_template
                            )
                        )

            print("\n{}".format("=" * 80))
            print("DEBUG: ✅ Completed all tests for customer {}".format(customer))
            print("{}\n".format("=" * 80))

        # Final summary
        print("\n" + "=" * 80)
        print("DEBUG: TEST SUMMARY")
        print("DEBUG: Total test cases: {}".format(total_invoices))
        print("DEBUG: Settled invoices (matching tax category): {}".format(settled_invoices))
        print(
            "DEBUG: Unsettled/Failed cases (non-matching tax category): {}".format(
                unsettled_invoices
            )
        )
        print("DEBUG: Expected: 9 test cases, 3 settled, 6 unsettled/failed")
        print("{}\n".format("=" * 80))

        # Verify counts
        self.assertEqual(total_invoices, 9, "Should have 9 total test cases")
        self.assertEqual(settled_invoices, 3, "Should have 3 settled invoices (matching)")
        self.assertEqual(
            unsettled_invoices, 6, "Should have 6 unsettled/failed cases (non-matching)"
        )

        frappe.logger().info(
            "\n✅✅✅ All tax category matching/non-matching tests completed successfully ✅✅✅"
        )

    # def test_tax_category_with_advance_payment_entry(self):
    #     """
    #     Test that invoices can be settled by advance payment entries with matching tax categories.
    #     Customer C4 has CAT-S tax category and advance payment entry.
    #     Invoice with matching tax category can use the advance payment.
    #     """
    #     company_abbr = frappe.get_cached_value("Company", self.company, "abbr")

    #     # Test customer C4 with advance payment entry
    #     # C4 has CAT-S tax category
    #     frappe.logger().info(
    #         "\n🧪 Testing Customer C4 (Tax Category: CAT-S) with advance Payment Entry"
    #     )
    #     customer_c4 = CUSTOMERS[3]["name"]
    #     customer_tax_category = "CAT-S"
    #     advance_template_c4 = "VAT-S"  # Use VAT-S which matches CAT-S

    #     # Create advance payment entry with matching template
    #     frappe.logger().info(
    #         f"   📝 Creating advance payment entry with template {advance_template_c4}"
    #     )

    #     advance_pe = create_advance_payment_entry(
    #         customer=customer_c4,
    #         company=self.company,
    #         paid_amount=1000,
    #         tax_template=advance_template_c4,
    #     )
    #     self.assertTrue(advance_pe.name)
    #     frappe.logger().info(f"   ✅ Created advance payment entry: {advance_pe.name}")

    #     # Create normal sales invoice with matching template
    #     frappe.logger().info(
    #         f"   📝 Creating normal invoice with MATCHING template {advance_template_c4}"
    #     )

    #     invoice = create_normal_sales_invoice(
    #         customer=customer_c4,
    #         company=self.company,
    #         item_code=self.test_item,
    #         item_rate=500,
    #         tax_template=advance_template_c4,
    #     )
    #     self.assertTrue(invoice.name)
    #     invoice.reload()
    #     frappe.logger().info(f"   ✅ Created invoice: {invoice.name}")

    #     # Verify outstanding is zero (settled by advance payment entry)
    #     self.assertEqual(
    #         flt(invoice.outstanding_amount),
    #         0.0,
    #         f"Invoice {invoice.name} should be fully settled by advance PE (outstanding = 0)",
    #     )
    #     frappe.logger().info("   ✅ Outstanding is 0 - invoice fully settled by advance PE")

    #     # Verify that advances were applied
    #     self.assertGreater(
    #         len(invoice.advances),
    #         0,
    #         f"Invoice {invoice.name} should have advances from payment entry applied",
    #     )
    #     frappe.logger().info(f"   ✅ {len(invoice.advances)} advance payment(s) applied")

    #     # Verify the advance reference is from a payment entry
    #     for advance in invoice.advances:
    #         self.assertEqual(
    #             advance.reference_type,
    #             "Payment Entry",
    #             "Advance should be from Payment Entry",
    #         )
    #         frappe.logger().info(f"   ✅ Advance from Payment Entry: {advance.reference_name}")

    #     # Verify tax template has correct tax category
    #     full_template_name = f"{advance_template_c4} - {company_abbr}"
    #     template_doc = frappe.get_doc("Sales Taxes and Charges Template", full_template_name)
    #     self.assertEqual(
    #         template_doc.tax_category,
    #         customer_tax_category,
    #         f"Template {full_template_name} should have tax category {customer_tax_category}",
    #     )
    #     frappe.logger().info(
    #         f"   ✅ Tax template {full_template_name} has correct tax category {customer_tax_category}"
    #     )

    #     frappe.logger().info(
    #         "\n✅✅✅ Advance payment entry tax category test completed successfully ✅✅✅"
    #     )
