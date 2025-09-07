import frappe
from erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment import UnreconcilePayment
from erpnext.accounts.utils import (
    cancel_exchange_gain_loss_journal,
    unlink_ref_doc_from_payment_entries,
    update_voucher_outstanding,
)
from frappe import _

from ksa_compliance.standard_doctypes.sales_invoice_advance import get_invoice_advance_payments


def unreconcile_from_advance_payment(
    company, voucher_type, voucher_no, against_voucher_type, against_voucher_no, allocated_amount
):
    unrecon = frappe.new_doc("Unreconcile Payment")
    unrecon.company = company
    unrecon.voucher_type = voucher_type
    unrecon.voucher_no = voucher_no
    unrecon.add_references()

    # remove unselected references
    unrecon.allocations = [
        x
        for x in unrecon.allocations
        if x.reference_doctype == against_voucher_type and x.reference_name == against_voucher_no
    ]
    new_allocations = []
    for allocation in unrecon.allocations:
        if (
            allocation.reference_doctype == against_voucher_type
            and allocation.reference_name == against_voucher_no
        ):
            allocation.allocated_amount = allocated_amount
            new_allocations.append(allocation)

    unrecon.allocations = new_allocations
    setattr(unrecon, "enable_unreconcile_from_advance_payment", True)
    unrecon.save().submit()


def prevent_un_reconcile_advance_payments(self, method):
    if hasattr(self, "enable_unreconcile_from_advance_payment"):
        setattr(self, "enable_unreconcile_from_advance_payment", False)
        return
    valid = True
    if self.voucher_type == "Payment Entry":
        payment_entry = frappe.get_doc(self.voucher_type, self.voucher_no)
        if (
            payment_entry.is_advance_payment == 1
            and payment_entry.payment_type == "Receive"
            and payment_entry.party_type == "Customer"
        ):
            frappe.msgprint(_("Cant UNRreconcile From Advance Payment Entry"))
            valid = False
    for allocation in self.allocations:
        if allocation.reference_doctype != "Sales Invoice":
            continue
        allocation_doc = frappe.get_doc(allocation.reference_doctype, allocation.reference_name)
        advance_payments = get_invoice_advance_payments(allocation_doc)
        if advance_payments:
            frappe.msgprint(
                _("Cant UNRreconcile {0}, Its Payed from Advance Payment Entry").format(
                    allocation.reference_name
                )
            )
            valid = False
    if not valid:
        message_log = frappe.get_message_log()
        error_messages = "\n".join(log["message"] for log in message_log)
        raise frappe.ValidationError(error_messages)


class CustomUnreconcilePayment(UnreconcilePayment):
    def on_submit(self):
        if self.voucher_type == "Payment Entry":
            payment_entry = frappe.get_doc(self.voucher_type, self.voucher_no)
            if (
                payment_entry.is_advance_payment == 1
                and payment_entry.party_type == "Customer"
                and payment_entry.payment_type == "Receive"
            ):
                self.unreconcile_advance_payment()
            else:
                super(CustomUnreconcilePayment, self).on_submit()

    def unreconcile_advance_payment(self):
        # todo: more granular unreconciliation
        for alloc in self.allocations:
            doc = frappe.get_doc(alloc.reference_doctype, alloc.reference_name)
            unlink_ref_doc_from_payment_entries(doc, self.voucher_no)
            cancel_exchange_gain_loss_journal(doc, self.voucher_type, self.voucher_no)

            # update outstanding amounts
            update_voucher_outstanding(
                alloc.reference_doctype,
                alloc.reference_name,
                alloc.account,
                alloc.party_type,
                alloc.party,
            )

            frappe.db.set_value("Unreconcile Payment Entries", alloc.name, "unlinked", True)
