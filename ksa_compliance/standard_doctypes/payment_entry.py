import frappe
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings


def get_company_default_taxes_and_charges_template(payment_entry):
    settings = ZATCABusinessSettings.for_company(payment_entry.company)
    return frappe.get_value(
        doctype="Sales Taxes and Charges Template",
        filters={
            "company": settings.company,
            "is_default": 1
        }
    )


def get_taxes_and_charges_details(payment_entry):
    item_tax_template = get_company_default_taxes_and_charges_template(payment_entry)
    taxes = get_taxes_and_charges("Sales Taxes and Charges Template", item_tax_template)[0]
    return taxes
