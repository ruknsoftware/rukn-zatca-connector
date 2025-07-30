import json

import frappe
from frappe.utils import flt
from frappe import qb
from frappe.query_builder.custom import ConstantColumn
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice
from erpnext.accounts.party import get_party_account
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings


def get_invoice_advance_payments(self: SalesInvoice | POSInvoice):
    sales_invoice_advance = frappe.qb.DocType("Sales Invoice Advance")
    payment_entry = frappe.qb.DocType("Payment Entry")
    advance_payments = []
    if hasattr(self, "__unsaved"):
        for sales_invoice_advance in self.advances:
            payment_entry = frappe.get_doc(sales_invoice_advance.reference_type, sales_invoice_advance.reference_name)
            if (
                payment_entry.is_advance_payment == True
                and payment_entry.party_type == "Customer"
                and payment_entry.payment_type == "Receive"
            ):
                advance_payments.append(frappe._dict(
                    allocated_amount=sales_invoice_advance.allocated_amount,
                    reference_name=sales_invoice_advance.reference_name,
                    remarks=sales_invoice_advance.remarks,
                    reference_row=sales_invoice_advance.reference_row,
                    advance_amount=sales_invoice_advance.advance_amount,
                    advance_payment_invoice=payment_entry.advance_payment_invoice,
                ))
        return advance_payments

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


@frappe.whitelist()
def get_invoice_applicable_advance_payments(self):
    self = json.loads(self)
    company = self.get("company")
    settings = ZATCABusinessSettings.for_company(company)
    if not settings.auto_apply_advance_payments:
        return []
    customer = self.get("customer")
    party_account = get_party_account(party_type="Customer", party=customer, company=company)
    payment_entry = qb.DocType("Payment Entry")
    advance_payment_entries = (
        qb.from_(payment_entry)
        .select(
            ConstantColumn("Payment Entry").as_("reference_type"),
            payment_entry.name.as_("reference_name"),
            payment_entry.posting_date,
            payment_entry.remarks,
            payment_entry.unallocated_amount.as_("amount"),
            payment_entry.source_exchange_rate.as_("exchange_rate"),
            payment_entry.paid_from_account_currency.as_("currency"),
        )
        .where(
            (payment_entry.paid_from == party_account)
            & (payment_entry.party_type == "Customer")
            & (payment_entry.party == customer)
            & (payment_entry.payment_type == "Receive")
            & (payment_entry.docstatus == 1)
            & (payment_entry.unallocated_amount.gt(0))
            & (payment_entry.is_advance_payment == True)
        )
        .orderby(payment_entry.posting_date)
    ).run(as_dict=1)
    advances = []
    advance_allocated = 0
    for advance_payment in advance_payment_entries:
        amount = self.get("grand_total")
        allocated_amount = min(amount - advance_allocated, advance_payment.amount)
        advance_allocated += flt(allocated_amount)

        advance_row = {
            "doctype": self.get("doctype") + " Advance",
            "reference_type": advance_payment.reference_type,
            "reference_name": advance_payment.reference_name,
            "reference_row": advance_payment.reference_row,
            "remarks": advance_payment.remarks,
            "advance_amount": flt(advance_payment.amount),
            "allocated_amount": allocated_amount,
            "ref_exchange_rate": flt(advance_payment.exchange_rate),  # exchange_rate of advance entry
        }

        advances.append(advance_row)
    return advances
