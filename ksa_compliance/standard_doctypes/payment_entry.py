import frappe
from frappe import _
from frappe.utils import  flt
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from erpnext.accounts.utils import get_account_currency
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings


class AdvancePaymentEntry(PaymentEntry):

    def check_is_advance_payment_entry(self) -> bool:
        return self.is_advance_payment and self.payment_type == "Receive" and self.party_type == "Customer"

    def add_bank_gl_entries(self, gl_entries):
        if self.check_is_advance_payment_entry():
            exchange_rate = self.get_exchange_rate()
            base_unallocated_amount = self.unallocated_amount * exchange_rate
            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": self.paid_to,
                        "account_currency": self.paid_to_account_currency,
                        "against": self.party,
                        "debit_in_account_currency": self.unallocated_amount,
                        "debit": base_unallocated_amount,
                        "cost_center": self.cost_center,
                    },
                    item=self,
                )
            )
        else:
            super().add_bank_gl_entries(gl_entries)

    def add_tax_gl_entries(self, gl_entries):
        if self.check_is_advance_payment_entry():
            self.add_advance_payment_tax_gl_entries(gl_entries)
        else:
            super().add_tax_gl_entries(gl_entries)

    def add_advance_payment_tax_gl_entries(self, gl_entries):
        for d in self.get("taxes"):
            account_currency = get_account_currency(d.account_head)
            if account_currency != self.company_currency:
                frappe.throw(_("Currency for {0} must be {1}").format(d.account_head, self.company_currency))

            dr_or_cr = "credit" if d.add_deduct_tax == "Add" else "debit"
            rev_dr_or_cr = "credit" if dr_or_cr == "debit" else "debit"

            against = self.party or self.paid_to

            tax_amount = d.tax_amount
            base_tax_amount = d.base_tax_amount

            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": d.account_head,
                        "against": against,
                        dr_or_cr: tax_amount,
                        dr_or_cr + "_in_account_currency": base_tax_amount
                        if account_currency == self.company_currency
                        else d.tax_amount,
                        "cost_center": d.cost_center,
                        "post_net_value": True,
                    },
                    account_currency,
                    item=d,
                )
            )
            settings = ZATCABusinessSettings.for_company(self.company)
            advance_payment_account = settings.advance_payment_account
            if advance_payment_account:
                if get_account_currency(advance_payment_account) != self.company_currency:
                    exchange_rate = self.target_exchange_rate
                    base_tax_amount = flt((tax_amount / exchange_rate), self.precision("paid_amount"))

                gl_entries.append(
                    self.get_gl_dict(
                        {
                            "account": advance_payment_account,
                            "against": against,
                            rev_dr_or_cr: tax_amount,
                            rev_dr_or_cr + "_in_account_currency": base_tax_amount
                            if account_currency == self.company_currency
                            else d.tax_amount,
                            "cost_center": self.cost_center,
                            "post_net_value": True,
                        },
                        account_currency,
                        item=d,
                    )
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
