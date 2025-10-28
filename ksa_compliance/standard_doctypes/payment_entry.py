import json

import frappe
from erpnext.accounts.general_ledger import (
    make_gl_entries,
    process_gl_map,
)
from erpnext.accounts.utils import get_account_currency
from frappe import _
from frappe.utils import flt

from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
    ZATCABusinessSettings,
)
from ksa_compliance.utils.advance_payment_entry_taxes_and_charges import get_taxes_and_charges
from ksa_compliance.utils.update_itemised_tax_data import (
    calculate_net_from_gross_included_in_print_rate,
    calculate_tax_amount_included_in_print_rate,
)


def prevent_settling_advance_invoice_from_payment_entry_references(doc, method):
    invoice_names = [
        ref.reference_name for ref in doc.references if ref.reference_doctype == "Sales Invoice"
    ]

    settings = ZATCABusinessSettings.for_company(doc.company)
    if not settings or not invoice_names or not settings.enable_zatca_integration:
        return
    sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
    sales_invoice = frappe.qb.DocType("Sales Invoice")
    advance_invoices = (
        frappe.qb.from_(sales_invoice_item)
        .join(sales_invoice)
        .on(sales_invoice_item.parent == sales_invoice.name)
        .select(sales_invoice_item.parent)
        .where(
            (sales_invoice_item.parent.isin(invoice_names))
            & (sales_invoice_item.item_code == settings.advance_payment_item)
            & (sales_invoice.is_return == 0)
        )
    ).run(as_dict=True)
    if advance_invoices:
        names = [invoice.parent for invoice in advance_invoices]
        frappe.throw(
            _("You cannot settle advance invoices from Payment Entry: {0}").format(
                ", ".join(names)
            )
        )


def set_advance_payment_entry_settling_references(payment_entry):
    advance_payment_entry = frappe.get_value(
        "Payment Entry",
        {
            "advance_payment_invoice": payment_entry.advance_payment_invoice,
            "payment_type": "Receive",
        },
    )
    advance_payment_entry_doc = frappe.get_doc("Payment Entry", advance_payment_entry)

    for reference in payment_entry.references:
        advance_payment_entry_reference = reference.as_dict().copy()
        advance_payment_entry_reference.reference_doctype = payment_entry.doctype
        advance_payment_entry_reference.reference_name = payment_entry.name
        advance_payment_entry_reference.total_amount = abs(
            advance_payment_entry_reference.total_amount
        )
        advance_payment_entry_reference.outstanding_amount = (
            -advance_payment_entry_reference.outstanding_amount
        )
        advance_payment_entry_reference.allocated_amount = abs(
            advance_payment_entry_reference.allocated_amount
        )
        advance_payment_entry_doc.append("references", advance_payment_entry_reference)

    advance_payment_entry_doc.total_allocated_amount += payment_entry.paid_amount
    advance_payment_entry_doc.base_total_allocated_amount += payment_entry.paid_amount
    advance_payment_entry_doc.unallocated_amount -= payment_entry.paid_amount
    advance_payment_entry_doc.flags.ignore_validate_update_after_submit = True
    advance_payment_entry_doc.save()


def add_tax_gl_entries(doc, method):
    settings = ZATCABusinessSettings.for_company(doc.company)
    if (
        not settings
        or not settings.enable_zatca_integration
        or settings.advance_payment_depends_on != "Payment Entry"
        or not doc.is_advance_payment_depends_on_entry
        or doc.payment_type not in ("Receive", "Pay")
    ):
        return
    tax = get_taxes_and_charges(doc).taxes[0]
    gl_entries = []

    account_currency = get_account_currency(tax.get("account_head"))
    if account_currency != doc.company_currency:
        frappe.throw(
            _("Currency for {0} must be {1}").format(tax.get("account_head"), doc.company_currency)
        )

    if doc.payment_type == "Pay":
        dr_or_cr = "debit" if tax.get("add_deduct_tax") == "Add" else "credit"
        rev_dr_or_cr = "credit" if dr_or_cr == "debit" else "debit"
        against = doc.party or doc.paid_from
    elif doc.payment_type == "Receive":
        dr_or_cr = "credit" if tax.get("add_deduct_tax") == "Add" else "debit"
        rev_dr_or_cr = "credit" if dr_or_cr == "debit" else "debit"
        against = doc.party or doc.paid_to

    tax_rate = tax.rate
    amount = flt(doc.paid_amount)
    net_amount = round(calculate_net_from_gross_included_in_print_rate(amount, tax_rate), 2)
    tax_amount = round(calculate_tax_amount_included_in_print_rate(amount, net_amount), 2)
    doc.db_set("unallocated_tax", tax_amount)
    doc.db_set("allocated_tax", 0.0)
    gl_entries.append(
        doc.get_gl_dict(
            {
                "account": tax.get("account_head"),
                "against": against,
                rev_dr_or_cr: tax_amount,
                rev_dr_or_cr
                + "_in_account_currency": (
                    tax_amount
                    if account_currency == doc.company_currency
                    else tax.get("tax_amount")
                ),
                "cost_center": tax.get("cost_center"),
                "post_net_value": True,
            },
            account_currency,
            item=tax,
        )
    )

    gl_entries.append(
        doc.get_gl_dict(
            {
                "account": settings.advance_payment_tax_account,
                "against": tax.get("account_head"),
                dr_or_cr: tax_amount,
                dr_or_cr + "_in_account_currency": tax_amount,
                "cost_center": tax.get("cost_center"),
                "post_net_value": True,
            },
            account_currency,
            item=tax,
        )
    )
    gl_entries = process_gl_map(gl_entries)
    make_gl_entries(gl_entries)


@frappe.whitelist()
def return_advance_payment_entry_doc(payment_entry_name, return_amount):

    payment_entry_doc = frappe.get_doc("Payment Entry", payment_entry_name)
    settings = ZATCABusinessSettings.for_company(payment_entry_doc.company)
    tax = get_taxes_and_charges(payment_entry_doc).taxes[0]
    tax_rate = tax.rate
    amount = flt(return_amount)
    if amount > payment_entry_doc.unallocated_amount:
        frappe.throw(title=_("Invalid Amount"), msg=_("Amount cannot exceed Unallocated Amount."))
    net_amount = round(calculate_net_from_gross_included_in_print_rate(amount, tax_rate), 2)
    tax_amount = round(calculate_tax_amount_included_in_print_rate(amount, net_amount), 2)

    tax_account_currency = get_account_currency(tax.get("account_head"))
    if tax_account_currency != payment_entry_doc.company_currency:
        frappe.throw(
            _("Currency for {0} must be {1}").format(
                tax.get("account_head"), payment_entry_doc.company_currency
            )
        )

    journal_entry = frappe.new_doc("Journal Entry")
    journal_entry.advance_payment_entry = payment_entry_doc.name
    journal_entry.voucher_type = "Journal Entry"
    journal_entry.company = payment_entry_doc.company
    journal_entry.posting_date = payment_entry_doc.posting_date
    journal_entry.cheque_no = payment_entry_doc.reference_no
    journal_entry.cheque_date = payment_entry_doc.reference_date
    journal_entry.mode_of_payment = payment_entry_doc.mode_of_payment

    paid_from_currency = get_account_currency(payment_entry_doc.paid_from)
    paid_to_currency = get_account_currency(payment_entry_doc.paid_to)

    accounts = [
        {
            "account": payment_entry_doc.paid_from,
            "party_type": payment_entry_doc.party_type,
            "party": payment_entry_doc.get("party"),
            "credit_in_account_currency": 0.0,
            "debit_in_account_currency": return_amount,
            "account_currency": paid_from_currency,
            "cost_center": payment_entry_doc.cost_center,
            "reference_type": "Payment Entry",
            "reference_name": payment_entry_name,
        },
        {
            "account": payment_entry_doc.paid_to,
            "credit_in_account_currency": return_amount,
            "debit_in_account_currency": 0.0,
            "account_currency": paid_to_currency,
            "cost_center": payment_entry_doc.cost_center,
            "reference_type": "Payment Entry",
            "reference_name": payment_entry_name,
        },
        {
            "account": tax.get("account_head"),
            "credit_in_account_currency": 0.0,
            "debit_in_account_currency": tax_amount,
            "account_currency": tax_account_currency,
            "cost_center": payment_entry_doc.cost_center,
            "reference_type": "Payment Entry",
            "reference_name": payment_entry_name,
        },
        {
            "account": settings.advance_payment_tax_account,
            "credit_in_account_currency": tax_amount,
            "debit_in_account_currency": 0.0,
            "account_currency": tax_account_currency,
            "cost_center": payment_entry_doc.cost_center,
            "against_account": tax.get("account_head"),
            "reference_type": "Payment Entry",
            "reference_name": payment_entry_name,
        },
    ]
    journal_entry.set("accounts", accounts)
    journal_entry.set_amounts_in_company_currency()
    journal_entry.set_total_debit_credit()
    journal_entry.save()
    journal_entry.submit()

    payment_entry_doc.append(
        "references",
        {
            "reference_doctype": journal_entry.doctype,
            "reference_name": journal_entry.name,
            "total_amount": return_amount,
            "outstanding_amount": 0.0,
            "allocated_amount": return_amount,
        },
    )

    payment_entry_doc.total_allocated_amount += flt(return_amount)
    payment_entry_doc.base_total_allocated_amount += flt(return_amount)
    payment_entry_doc.unallocated_amount -= flt(return_amount)

    payment_entry_doc.allocated_tax += tax_amount
    payment_entry_doc.unallocated_tax -= tax_amount
    payment_entry_doc.flags.ignore_validate_update_after_submit = True
    payment_entry_doc.save()

    return journal_entry.name
