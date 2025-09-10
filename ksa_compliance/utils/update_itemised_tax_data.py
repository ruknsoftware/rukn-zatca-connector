import frappe
from erpnext.controllers.taxes_and_totals import get_itemised_tax
from frappe import _
from frappe.utils import flt


def update_itemised_tax_data(doc):
    if not doc.items:
        return

    meta = frappe.get_meta(doc.items[0].doctype)
    if not meta.has_field("tax_rate"):
        return

    itemised_tax = get_itemised_tax(doc.taxes)

    def determine_if_export(doc):
        if doc.doctype != "Sales Invoice":
            return False

        if not doc.customer_address:
            if not doc.total_taxes_and_charges:
                frappe.msgprint(
                    _("Please set Customer Address to determine if the transaction is an export."),
                    alert=True,
                )

            return False

        company_country = frappe.get_cached_value("Company", doc.company, "country")
        customer_country = frappe.db.get_value("Address", doc.customer_address, "country")

        if company_country != customer_country:
            return True

        return False

    is_export = determine_if_export(doc)
    included_in_print_rate = any(tax.included_in_print_rate for tax in doc.get("taxes", []))
    for row in doc.items:
        tax_rate, tax_amount = 0.0, 0.0
        # dont even bother checking in item tax template as it contains both input and output accounts - double the tax rate
        item_code = row.item_code or row.item_name
        if itemised_tax.get(item_code):
            for tax in itemised_tax.get(item_code).values():
                _tax_rate = flt(tax.get("tax_rate", 0), row.precision("tax_rate"))
                tax_rate += _tax_rate
                if included_in_print_rate:
                    amount = flt(row.amount, row.precision("amount"))
                    net_from_gross = amount / (1 + (_tax_rate / 100))
                    tax_amount += flt(amount - net_from_gross, row.precision("tax_amount"))
                else:
                    tax_amount += flt(
                        (row.net_amount * _tax_rate) / 100, row.precision("tax_amount")
                    )

        if not tax_rate or row.get("is_zero_rated"):
            row.is_zero_rated = is_export or frappe.get_cached_value(
                "Item", row.item_code, "is_zero_rated"
            )

        row.tax_rate = flt(tax_rate, row.precision("tax_rate"))
        row.tax_amount = flt(tax_amount, row.precision("tax_amount"))
        row.total_amount = flt((row.net_amount + row.tax_amount), row.precision("total_amount"))
