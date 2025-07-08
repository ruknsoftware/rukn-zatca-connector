import frappe
from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import PaymentReconciliation


class CustomPaymentReconciliation(PaymentReconciliation):
    def get_payment_entry_conditions(self):
        conditions = super().get_payment_entry_conditions()
        if self.party_type == "Customer":
            pe = frappe.qb.DocType("Payment Entry")
            conditions.append(pe.is_advance_payment == 0)
        return conditions
