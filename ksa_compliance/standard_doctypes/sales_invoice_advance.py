import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice


def get_invoice_advance_payments(self: SalesInvoice | POSInvoice):
    sales_invoice_advance = frappe.qb.DocType("Sales Invoice Advance")
    payment_entry = frappe.qb.DocType("Payment Entry")

    return (
        frappe.qb.from_(sales_invoice_advance)
        .join(payment_entry).on(payment_entry.name == sales_invoice_advance.reference_name)
        .select(
            sales_invoice_advance.allocated_amount,
            sales_invoice_advance.reference_name,
            sales_invoice_advance.allocated_amount,
            payment_entry.advance_payment_invoice,
        ).where(
            (payment_entry.is_advance_payment == True)
            &(payment_entry.payment_type == "Receive")
            & (payment_entry.party_type == "Customer")
            & (sales_invoice_advance.parent == self.name)
        )
    ).run(as_dict=True)
