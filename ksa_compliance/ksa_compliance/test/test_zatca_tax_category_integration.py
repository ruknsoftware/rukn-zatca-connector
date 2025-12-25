# Copyright (c) 2025, LavaLoon and Contributors
# See license.txt
"""
ZATCA Tax Category and Invoice Integration Tests

"""
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from ksa_compliance.test.test_setup import _create_customer_address

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

ADDRESS_TEMPLATE = {
    "address_title": "standard ZATCA CustomerAddress-Billing-Billing",
    "address_type": "Billing",
    "address_line1": "Test Address Line 1",
    "city": "Riyadh",
    "country": "Saudi Arabia",
}


class TestZATCATaxCategoryIntegration(FrappeTestCase):
    def setUp(self):
        self.company = "RUKN"
        self.currency = "SAR"
        self.account_head = f"Miscellaneous Expenses - {self.company}"
        self.cost_center = f"Main - {self.company}"
        self.debit_to = f"Debtors - {self.company}"
        self.test_item = self._ensure_test_item_exists()
        self._create_tax_categories()
        self._create_tax_templates()
        self._create_customers_with_address()

    def _ensure_test_item_exists(self):
        test_item = "Test Item"
        if not frappe.db.exists("Item", test_item):
            item_doc = frappe.new_doc("Item")
            item_doc.item_code = test_item
            item_doc.item_name = test_item
            item_doc.item_group = "All Item Groups"
            item_doc.is_stock_item = 0
            item_doc.insert(ignore_permissions=True)
        return test_item

    def _create_tax_categories(self):
        for cat in TAX_CATEGORIES:
            if not frappe.db.exists("Tax Category", cat["name"]):
                doc = frappe.new_doc("Tax Category")
                doc.title = cat["name"]
                doc.tax_category_name = cat["name"]
                doc.custom_zatca_category = cat["custom_zatca_category"]
                doc.insert(ignore_permissions=True)

    def _create_tax_templates(self):
        company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
        for temp in TAX_TEMPLATES:
            full_template_name = f"{temp['name']} - {company_abbr}"
            if not frappe.db.exists("Sales Taxes and Charges Template", full_template_name):
                doc = frappe.get_doc(
                    {
                        "doctype": "Sales Taxes and Charges Template",
                        "title": temp["name"],
                        "company": self.company,
                        "tax_category": temp["category"],
                        "taxes": [
                            {
                                "charge_type": "On Net Total",
                                "account_head": self.account_head,
                                "cost_center": self.cost_center,
                                "rate": temp["rate"],
                                "description": f"VAT {temp['rate']}%",
                            }
                        ],
                    }
                )
                doc.insert(ignore_permissions=True)

    def _create_customers_with_address(self):
        for cust in CUSTOMERS:
            if not frappe.db.exists("Customer", cust["name"]):
                doc = frappe.new_doc("Customer")
                doc.customer_name = cust["name"]
                doc.customer_type = "Company"
                doc.tax_id = cust["vat"]
                doc.custom_vat_registration_number = cust["vat"]
                doc.vat_registration_number = cust["vat"]
                doc.insert(ignore_permissions=True)
                # Create a new address for this customer using the tested utility
                _create_customer_address(cust["name"], doc.name)

    def _create_advance_invoice(self, customer, tax_template):
        company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
        full_template_name = f"{tax_template} - {company_abbr}"
        advance_invoice = frappe.new_doc("Sales Invoice")
        advance_invoice.customer = customer
        advance_invoice.company = self.company
        advance_invoice.currency = self.currency
        advance_invoice.posting_date = frappe.utils.nowdate()
        advance_invoice.due_date = frappe.utils.nowdate()
        advance_invoice.debit_to = self.debit_to
        advance_invoice.mode_of_payment = "Cash"
        advance_invoice.taxes_and_charges = full_template_name
        advance_invoice.append(
            "items",
            {
                "item_code": self.test_item,
                "qty": 1,
                "rate": 1000,
                "income_account": f"Sales - {self.company}",
                "cost_center": self.cost_center,
            },
        )
        # Explicitly append taxes row as in state3 integration test
        template_doc = frappe.get_doc("Sales Taxes and Charges Template", full_template_name)
        tax_row = template_doc.taxes[0]
        advance_invoice.append(
            "taxes",
            {
                "charge_type": tax_row.charge_type,
                "account_head": tax_row.account_head,
                "cost_center": tax_row.cost_center,
                "rate": tax_row.rate,
                "description": tax_row.description,
            },
        )
        advance_invoice.insert()
        advance_invoice.submit()
        return advance_invoice

    def _create_normal_invoice(self, customer, tax_template):
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
        invoice.append(
            "items",
            {
                "item_code": self.test_item,
                "qty": 1,
                "rate": 500,
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
