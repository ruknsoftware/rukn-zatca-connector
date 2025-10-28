import frappe

from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
    ZATCABusinessSettings,
)
from ksa_compliance.utils.advance_payment_invoice import invoice_has_advance_item


def set_party_details_on_advance_invoice(self, method):
    if self.voucher_type == "Sales Invoice":
        sales_invoice = frappe.get_doc("Sales Invoice", self.voucher_no)
        settings = ZATCABusinessSettings.for_company(sales_invoice.company)
        if not settings.enable_zatca_integration:
            return
        if settings and invoice_has_advance_item(sales_invoice, settings):
            income_account = sales_invoice.items[0].income_account
            if not self.party and self.account == income_account:
                self.party_type = "Customer"
                self.party = sales_invoice.customer
