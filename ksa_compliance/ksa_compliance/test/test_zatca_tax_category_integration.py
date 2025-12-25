# Copyright (c) 2025, LavaLoon and Contributors
# See license.txt
"""
ZATCA Tax Category and Invoice Integration Tests

"""
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

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

    def _create_invoice(self, customer, tax_template, item_rate, mode_of_payment):
        """Generic method to create an invoice with configurable item rate and payment mode."""
        company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
        full_template_name = f"{tax_template} - {company_abbr}"
        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = customer
        invoice.company = self.company
        invoice.currency = self.currency
        invoice.posting_date = frappe.utils.nowdate()
        invoice.due_date = frappe.utils.nowdate()
        invoice.debit_to = self.debit_to
        invoice.taxes_and_charges = full_template_name
        invoice.mode_of_payment = mode_of_payment
        invoice.append(
            "items",
            {
                "item_code": self.test_item,
                "qty": 1,
                "rate": item_rate,
                "income_account": f"Sales - {self.company}",
                "cost_center": self.cost_center,
            },
        )
        # Explicitly append taxes row as in state3 integration test
        template_doc = frappe.get_doc("Sales Taxes and Charges Template", full_template_name)
        tax_row = template_doc.taxes[0]
        invoice.append(
            "taxes",
            {
                "charge_type": tax_row.charge_type,
                "account_head": tax_row.account_head,
                "cost_center": tax_row.cost_center,
                "rate": tax_row.rate,
                "description": tax_row.description,
            },
        )
        invoice.insert()
        invoice.submit()
        return invoice

    def _create_advance_invoice(self, customer, tax_template):
        return self._create_invoice(customer, tax_template, item_rate=1000, mode_of_payment="Cash")

    def _create_normal_invoice(self, customer, tax_template):
        return self._create_invoice(customer, tax_template, item_rate=500, mode_of_payment=None)

    def test_tax_category_and_invoice_flow(self):
        """
        For each customer, create an advance invoice with VAT-S, then 3 normal invoices with each template.
        Only the matching template should be valid for the customer.
        """
        company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
        template_map = ["VAT-S", "VAT-Z", "VAT-E"]
        for idx, cust in enumerate(CUSTOMERS):
            customer = cust["name"]
            advance_template = template_map[idx]
            advance_invoice = self._create_advance_invoice(customer, advance_template)
            self.assertTrue(advance_invoice.name)
            # Now create 3 normal invoices, one for each template
            for i, temp in enumerate(template_map):
                invoice = self._create_normal_invoice(customer, temp)
                self.assertTrue(invoice.name)
                # Only the matching template should match the customer's expected tax category
                expected_category = TAX_CATEGORIES[i]["name"]
                full_template_name = f"{temp} - {company_abbr}"
                template_doc = frappe.get_doc(
                    "Sales Taxes and Charges Template", full_template_name
                )
                self.assertEqual(template_doc.tax_category, expected_category)
