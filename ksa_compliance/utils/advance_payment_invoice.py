import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
    ZATCABusinessSettings,
)


@frappe.whitelist()
def get_advance_payment_item(company):
    return frappe.get_value(
        "ZATCA Business Settings",
        {"company": company, "advance_payment_depends_on": "Sales Invoice"},
        "advance_payment_item",
    )


def invoice_has_advance_item(self: SalesInvoice, settings: ZATCABusinessSettings) -> bool:
    if settings.advance_payment_depends_on != "Sales Invoice":
        return False
    items = [item.item_code for item in self.items]
    return settings.advance_payment_item in items
