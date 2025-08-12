import frappe
from frappe import _
from erpnext.controllers.accounts_controller import get_taxes_and_charges
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
    advance_invoices = (
        frappe.qb.from_(sales_invoice_item)
        .select(sales_invoice_item.parent)
        .where(
            sales_invoice_item.parent.isin(invoice_names)
            & sales_invoice_item.item_code == settings.advance_payment_item
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
