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
            sales_invoice_advance.remarks,
            sales_invoice_advance.reference_row,
            sales_invoice_advance.advance_amount,
            sales_invoice_advance.exchange_gain_loss,
            sales_invoice_advance.ref_exchange_rate,

            payment_entry.advance_payment_invoice,
        ).where(
            (payment_entry.is_advance_payment == True)
            &(payment_entry.payment_type == "Receive")
            & (payment_entry.party_type == "Customer")
            & (sales_invoice_advance.parent == self.name)
        )
    ).run(as_dict=True)



def set_advance_payment_invoice_settling_gl_entries(advance_payment):
    advance_payment_invoice = frappe.get_doc("Sales Invoice", advance_payment.advance_payment_invoice)
    item = advance_payment_invoice.items[0]
    gl_entries = advance_payment_invoice.get_gl_entries()
    income_account = item.income_account
    tax_amount = calculate_advance_payment_tax_amount(advance_payment, advance_payment_invoice)
    advance_gl_entries = []
    for gl_entry in gl_entries:
        if gl_entry.account == income_account:
            amount = advance_payment.allocated_amount - tax_amount
        elif gl_entry.account == advance_payment_invoice.debit_to:
            amount = advance_payment.allocated_amount
        else:
            amount = tax_amount

        advance_gl_entry = gl_entry.copy()

        if advance_gl_entry.debit != 0.0:
            advance_gl_entry['debit'] = 0.0
            advance_gl_entry['debit_in_account_currency'] = 0.0
            advance_gl_entry['credit'] = amount
            advance_gl_entry['credit_in_account_currency'] = amount
        else:
            advance_gl_entry['debit'] = amount
            advance_gl_entry['debit_in_account_currency'] = amount
            advance_gl_entry['credit'] = 0.0
            advance_gl_entry['credit_in_account_currency'] = 0.0
        advance_gl_entries.append(advance_gl_entry)
    advance_payment_invoice.make_gl_entries(advance_gl_entries)


def calculate_advance_payment_tax_amount(advance_payment, advance_payment_invoice):
    return round(((advance_payment.allocated_amount * advance_payment_invoice.base_total_taxes_and_charges) / advance_payment_invoice.grand_total),2)


def get_prepayment_info(self: SalesInvoice | POSInvoice):
    advance_payments = get_invoice_advance_payments(self)
    for idx, advance_payment in enumerate(advance_payments, start=1):
        advance_payment_invoice = frappe.get_doc('Sales Invoice', advance_payment.advance_payment_invoice)
        item = advance_payment_invoice.items[0]
        advance_payment["tax_percent"] = abs(item.tax_rate or 0.0)
        advance_payment["tax_amount"] = calculate_advance_payment_tax_amount(advance_payment, advance_payment_invoice)
        advance_payment["amount"] = round(advance_payment.allocated_amount - advance_payment["tax_amount"], 2)
        advance_payment["idx"] = idx
    return advance_payments
