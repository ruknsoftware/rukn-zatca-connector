import frappe
from frappe import _
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from erpnext.accounts.general_ledger import (
	make_gl_entries,
	process_gl_map,
)
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings


def prevent_settling_advance_invoice_from_payment_entry_references(doc, method):
    invoice_names = [
        ref.reference_name
        for ref in doc.references
        if ref.reference_doctype == "Sales Invoice"
    ]

    settings = ZATCABusinessSettings.for_company(doc.company)
    if not settings or not invoice_names:
        return
    sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
    sales_invoice = frappe.qb.DocType("Sales Invoice")
    advance_invoices = (
        frappe.qb.from_(sales_invoice_item)
        .join(sales_invoice).on(sales_invoice_item.parent == sales_invoice.name)
        .select(sales_invoice_item.parent)
        .where(
            (sales_invoice_item.parent.isin(invoice_names))
            & (sales_invoice_item.item_code == settings.advance_payment_item)
            & (sales_invoice.is_return == False)
        )
    ).run(as_dict=True)
    if advance_invoices:
        names = [invoice.parent for invoice in advance_invoices]
        frappe.throw(
            _("You cannot settle advance invoices from Payment Entry: {0}")
            .format(", ".join(names))
        )

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


def set_advance_payment_entry_settling_gl_entries(payment_entry):
    advance_payment_entry = frappe.get_value("Payment Entry", {
        "advance_payment_invoice": payment_entry.advance_payment_invoice,
        "payment_type": "Receive"
    })
    advance_payment_entry_doc = frappe.get_doc("Payment Entry", advance_payment_entry)

    if advance_payment_entry_doc.payment_type in ("Receive", "Pay") and not advance_payment_entry_doc.get("party_account_field"):
        advance_payment_entry_doc.setup_party_account_field()

    frappe_version = frappe.__version__
    if frappe_version.startswith("15"):
        advance_payment_entry_doc.set_transaction_currency_and_rate()

    payment_entry_gls = []

    party_gl_entries = []
    advance_payment_entry_doc.add_party_gl_entries(party_gl_entries)
    payment_entry_gls.append(party_gl_entries[-1])

    bank_gl_entries = []
    advance_payment_entry_doc.add_bank_gl_entries(bank_gl_entries)
    payment_entry_gls.extend(bank_gl_entries)

    payment_entry_gls = process_gl_map(payment_entry_gls)

    advance_gl_entries = []
    for gl_entry in payment_entry_gls:
        advance_gl_entry = gl_entry.copy()

        if advance_gl_entry.debit != 0.0:
            advance_gl_entry['debit'] = 0.0
            advance_gl_entry['debit_in_account_currency'] = 0.0
            advance_gl_entry['credit'] = payment_entry.paid_amount
            advance_gl_entry['credit_in_account_currency'] = payment_entry.paid_amount
        else:
            advance_gl_entry['debit'] = payment_entry.paid_amount
            advance_gl_entry['debit_in_account_currency'] = payment_entry.paid_amount
            advance_gl_entry['credit'] = 0.0
            advance_gl_entry['credit_in_account_currency'] = 0.0
        advance_gl_entries.append(advance_gl_entry)
    make_gl_entries(advance_gl_entries)

    advance_payment_entry_doc.total_allocated_amount += payment_entry.paid_amount
    advance_payment_entry_doc.base_total_allocated_amount += payment_entry.paid_amount
    advance_payment_entry_doc.unallocated_amount -= payment_entry.paid_amount
    advance_payment_entry_doc.flags.ignore_validate_update_after_submit = True
    advance_payment_entry_doc.save()
