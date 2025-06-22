import frappe
from frappe import _
from frappe.utils import  flt
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from erpnext.accounts.utils import get_account_currency
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings


class AdvancePaymentEntry(PaymentEntry):

    def add_tax_gl_entries(self, gl_entries):
        if self.is_advance_payment:
            self.add_advance_payment_tax_gl_entries(gl_entries)
        else:
            super().add_tax_gl_entries(gl_entries)

    def add_advance_payment_tax_gl_entries(self, gl_entries):
        taxes = get_taxes_and_charges_details(self)
        taxes["cost_center"] = self.cost_center
        taxes["tax_amount"] = taxes["base_tax_amount"] = self.tax_amount
        taxes["total"] = self.net_total
        account_currency = get_account_currency(taxes.account_head)
        if account_currency != self.company_currency:
            frappe.throw(
                _("Currency for {0} must be {1}").format(taxes.account_head, self.company_currency))

        if self.payment_type in ("Pay", "Internal Transfer"):
            dr_or_cr = "debit" if taxes.add_deduct_tax == "Add" else "credit"
            rev_dr_or_cr = "credit" if dr_or_cr == "debit" else "debit"
            against = self.party or self.paid_from
        elif self.payment_type == "Receive":
            dr_or_cr = "credit" if taxes.add_deduct_tax == "Add" else "debit"
            rev_dr_or_cr = "credit" if dr_or_cr == "debit" else "debit"
            against = self.party or self.paid_to

        tax_amount = taxes.tax_amount
        base_tax_amount = taxes.base_tax_amount

        gl_entries.append(
            self.get_gl_dict(
                {
                    "account": taxes.account_head,
                    "against": against,
                    dr_or_cr: tax_amount,
                    dr_or_cr + "_in_account_currency": base_tax_amount
                    if account_currency == self.company_currency
                    else taxes.tax_amount,
                    "cost_center": taxes.cost_center,
                    "post_net_value": True,
                },
                account_currency,
                item=taxes,
            )
        )
        tax_gl_entry = gl_entries[0]
        settings = ZATCABusinessSettings.for_company(self.company)
        advance_payment_account = settings.advance_payment_account
        if get_account_currency(advance_payment_account) != self.company_currency:
            if self.payment_type == "Receive":
                exchange_rate = self.target_exchange_rate
            elif self.payment_type in ["Pay", "Internal Transfer"]:
                exchange_rate = self.source_exchange_rate
            base_tax_amount = flt((tax_amount / exchange_rate), self.precision("paid_amount"))

        gl_entries.append(
            self.get_gl_dict(
                {
                    "account": advance_payment_account,
                    "against": against,
                    rev_dr_or_cr: tax_amount,
                    rev_dr_or_cr + "_in_account_currency": base_tax_amount
                    if account_currency == self.company_currency
                    else tax_gl_entry.tax_amount,
                    "cost_center": self.cost_center,
                    "post_net_value": True,
                },
                account_currency,
                item=tax_gl_entry,
            )
        )


def set_advance_payment_amounts(doc, method):
    if not doc.is_advance_payment:
        return
    tax_rate = get_taxes_and_charges_details(doc).get("rate")
    doc.net_total = round(doc.base_paid_amount / (1 + (tax_rate / 100)))
    doc.tax_amount = round(doc.base_paid_amount - doc.net_total)


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
