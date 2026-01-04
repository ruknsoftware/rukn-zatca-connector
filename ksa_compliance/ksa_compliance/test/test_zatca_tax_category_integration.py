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
from ksa_compliance.test.test_setup import _create_tax_category as create_tax_category
from ksa_compliance.test.test_setup import _create_tax_template as create_tax_template
from ksa_compliance.test.test_setup import _create_test_item as create_test_item

CUSTOMERS = [
    {"name": "C1", "vat": "311633596400003"},
    {"name": "C2", "vat": "311605596400003"},
    {"name": "C3", "vat": "311609592200003"},
    {"name": "C4", "vat": "311609592200004"},  # Customer for advance payment entry test
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
        create_tax_category()
        self._create_tax_templates()
        self._create_customers_with_address()

    def _create_tax_templates(self):
        for temp in TAX_TEMPLATES:
            create_tax_template(self.company, temp["category"])

    def _create_customers_with_address(self):
        for cust in CUSTOMERS:
            create_standard_customer(
                cust["name"],
                tax_category_name=None,  # No specific tax category for these customers
                with_address=True,
            )

    def test_tax_category_and_invoice_flow(self):
        """
        For each customer, create an advance invoice with VAT-S, then 3 normal invoices with each template.
        Only the matching template should be valid for the customer.
        Also verify that payment entries are created and settlements happen correctly.
        """
        company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
        template_map = ["VAT-S", "VAT-Z", "VAT-E"]

        # Test first 3 customers with advance sales invoice
        for idx, cust in enumerate(CUSTOMERS[:3]):
            customer = cust["name"]
            advance_template = template_map[idx]

            frappe.logger().info(
                f"\n🧪 Testing Customer {customer} with advance SI and template {advance_template}"
            )

            # Create advance invoice using helper
            advance_invoice = create_advance_sales_invoice(
                customer=customer, company=self.company, rate=1000, tax_template=advance_template
            )
            self.assertTrue(advance_invoice.name)
            frappe.logger().info(f"   ✅ Created advance invoice: {advance_invoice.name}")

            # Now create 3 normal invoices, one for each template
            for i, temp in enumerate(template_map):
                frappe.logger().info(f"   📝 Creating normal invoice with template {temp}")

                # Create normal invoice using helper
                invoice = create_normal_sales_invoice(
                    customer=customer,
                    company=self.company,
                    item_code=self.test_item,
                    item_rate=500,
                    tax_template=temp,
                )
                self.assertTrue(invoice.name)
                invoice.reload()

                # Check if this template matches the customer's advance template
                if temp == advance_template:
                    frappe.logger().info(
                        f"   ✅ Template {temp} matches advance template {advance_template}"
                    )

                    # Verify outstanding is zero (settled by advance)
                    self.assertEqual(
                        flt(invoice.outstanding_amount),
                        0.0,
                        f"Invoice {invoice.name} should be fully settled (outstanding = 0)",
                    )
                    frappe.logger().info("   ✅ Outstanding is 0 - invoice fully settled")

                    # Verify that advances were applied
                    self.assertGreater(
                        len(invoice.advances),
                        0,
                        f"Invoice {invoice.name} should have advances applied",
                    )
                    frappe.logger().info(f"   ✅ {len(invoice.advances)} advance(s) applied")

                    # Verify payment entry exists for the advance invoice
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
                    frappe.logger().info(f"   ✅ Payment entry created: {payment_entries[0].name}")
                else:
                    frappe.logger().info(
                        f"   ℹ️  Template {temp} does NOT match advance template {advance_template}"
                    )

                # Verify tax category matches expected
                expected_category = TAX_CATEGORIES[i]["name"]
                full_template_name = f"{temp} - {company_abbr}"
                template_doc = frappe.get_doc(
                    "Sales Taxes and Charges Template", full_template_name
                )
                self.assertEqual(template_doc.tax_category, expected_category)

        # Test 4th customer (C4) with advance payment entry
        frappe.logger().info("\n🧪 Testing Customer C4 with advance Payment Entry")
        customer_c4 = CUSTOMERS[3]["name"]
        advance_template_c4 = "VAT-S"  # Use VAT-S as the advance template

        # Create 3 advance payment entries, one for each tax template
        for i, temp in enumerate(template_map):
            frappe.logger().info(f"   📝 Creating advance payment entry with template {temp}")

            # Create advance payment entry using helper
            advance_pe = create_advance_payment_entry(
                customer=customer_c4, company=self.company, paid_amount=1000, tax_template=temp
            )
            self.assertTrue(advance_pe.name)
            frappe.logger().info(f"   ✅ Created advance payment entry: {advance_pe.name}")

        # Now create 3 normal sales invoices with different tax templates
        for i, temp in enumerate(template_map):
            frappe.logger().info(f"   📝 Creating normal invoice with template {temp}")

            invoice = create_normal_sales_invoice(
                customer=customer_c4,
                company=self.company,
                item_code=self.test_item,
                item_rate=500,
                tax_template=temp,
            )
            self.assertTrue(invoice.name)
            invoice.reload()

            # Check if this template matches the advance template
            if temp == advance_template_c4:
                frappe.logger().info(
                    f"   ✅ Template {temp} matches advance template {advance_template_c4}"
                )

                # Verify outstanding is zero (settled by advance payment entry)
                self.assertEqual(
                    flt(invoice.outstanding_amount),
                    0.0,
                    f"Invoice {invoice.name} should be fully settled by advance PE (outstanding = 0)",
                )
                frappe.logger().info(
                    "   ✅ Outstanding is 0 - invoice fully settled by advance PE"
                )

                # Verify that advances were applied
                self.assertGreater(
                    len(invoice.advances),
                    0,
                    f"Invoice {invoice.name} should have advances from payment entry applied",
                )
                frappe.logger().info(f"   ✅ {len(invoice.advances)} advance payment(s) applied")

                # Verify the advance reference is from a payment entry
                for advance in invoice.advances:
                    self.assertEqual(
                        advance.reference_type,
                        "Payment Entry",
                        "Advance should be from Payment Entry",
                    )
                    frappe.logger().info(
                        f"   ✅ Advance from Payment Entry: {advance.reference_name}"
                    )
            else:
                frappe.logger().info(
                    f"   ℹ️  Template {temp} does NOT match advance template {advance_template_c4}"
                )
                # For non-matching templates, invoice should have outstanding > 0
                self.assertGreater(
                    flt(invoice.outstanding_amount),
                    0,
                    f"Invoice {invoice.name} should have outstanding > 0 (not settled)",
                )
                frappe.logger().info("   ✅ Outstanding > 0 - invoice NOT settled (as expected)")

        frappe.logger().info(
            "\n✅✅✅ All tax category and settlement tests completed successfully ✅✅✅"
        )
