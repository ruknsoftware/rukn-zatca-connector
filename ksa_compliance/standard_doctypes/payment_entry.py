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


def prevent_settling_advance_invoice_from_payment_entry_references(doc, method):
    invoice_names = [
        ref.reference_name for ref in doc.references if ref.reference_doctype == "Sales Invoice"
    ]

    settings = ZATCABusinessSettings.for_company(doc.company)
    if not settings or not invoice_names:
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


def get_company_default_taxes_and_charges_template(payment_entry):
    settings = ZATCABusinessSettings.for_company(payment_entry.company)
    return frappe.get_value(
        doctype="Sales Taxes and Charges Template",
        filters={"company": settings.company, "is_default": 1},
    )


def get_taxes_and_charges(payment_entry):
    item_tax_template = get_company_default_taxes_and_charges_template(payment_entry)
    return frappe.get_doc("Sales Taxes and Charges Template", item_tax_template)


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
        or settings.advance_payment_depends_on != "Payment Entry"
        or not doc.is_advance_payment_depends_on_entry
        or doc.doc.payment_type not in ("Receive", "Pay")
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
    net_amount = round(amount / (1 + (tax_rate / 100)), 2)
    tax_amount = round(flt(amount - net_amount), 2)

    gl_entries.append(
        doc.get_gl_dict(
            {
                "account": tax.get("account_head"),
                "against": against,
                dr_or_cr: tax_amount,
                dr_or_cr
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
                rev_dr_or_cr: tax_amount,
                rev_dr_or_cr + "_in_account_currency": tax_amount,
                "cost_center": tax.get("cost_center"),
                "post_net_value": True,
            },
            account_currency,
            item=tax,
        )
    )
    gl_entries = process_gl_map(gl_entries)
    make_gl_entries(gl_entries)
