from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings


def is_advance_payment_invoice(self: SalesInvoice, settings: ZATCABusinessSettings) -> bool:
    items = [item.item_code for item in self.items]
    return settings.advance_payment_item in items
