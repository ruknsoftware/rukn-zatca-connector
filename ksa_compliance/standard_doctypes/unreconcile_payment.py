import frappe
from erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment import UnreconcilePayment
from erpnext.accounts.utils import (
    cancel_exchange_gain_loss_journal,
    remove_ref_doc_link_from_jv,
    remove_ref_doc_link_from_pe,
    update_accounting_ledgers_after_reference_removal,
    update_voucher_outstanding,
)
from frappe import _, qb
from frappe.utils import flt

from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
    ZATCABusinessSettings,
)
from ksa_compliance.standard_doctypes.sales_invoice_advance import (
    get_invoice_advance_payments,
    is_advance_payment_condition,
)
from ksa_compliance.zatca_guard import is_zatca_enabled


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
    settings = ZATCABusinessSettings.for_company(self.company)
    if getattr(settings, "enable_zatca_integration", False):
        return
    if hasattr(self, "enable_unreconcile_from_advance_payment"):
        setattr(self, "enable_unreconcile_from_advance_payment", False)
        return
    valid = True
    if self.voucher_type == "Payment Entry":
        payment_entry = frappe.get_doc(self.voucher_type, self.voucher_no)
        is_advance_payment = is_advance_payment_condition(
            payment_entry, settings.advance_payment_depends_on
        )
        if (
            is_advance_payment
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
            if not is_zatca_enabled(payment_entry.company):
                return super(CustomUnreconcilePayment, self).on_submit()

            settings = ZATCABusinessSettings.for_company(payment_entry.company)
            if not settings:
                return super(CustomUnreconcilePayment, self).on_submit()
            is_advance_payment = is_advance_payment_condition(
                payment_entry, settings.advance_payment_depends_on
            )
            if (
                is_advance_payment
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
            unlink_ref_doc_from_payment_entries(doc, self.voucher_no, alloc.allocated_amount)
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


def remove_ref_from_advance_section(
    ref_doc: object = None, payment_name=None, allocated_amount=None
):
    # TODO: this might need some testing
    if ref_doc.doctype in ("Sales Invoice", "Purchase Invoice"):
        advances = ref_doc.advances
        ref_doc.set("advances", [])
        adv_type = qb.DocType(f"{ref_doc.doctype} Advance")
        for advance in advances:
            if advance.reference_name != payment_name:
                continue
            elif advance.allocated_amount != allocated_amount:
                updated_allocated_amount = round(
                    abs(advance.allocated_amount - allocated_amount), 2
                )

                query = (
                    qb.update(adv_type)
                    .set(adv_type.allocated_amount, updated_allocated_amount)
                    .where(
                        (adv_type.parent == ref_doc.name)
                        & (adv_type.reference_name == payment_name)
                    )
                )
                query.run()
            elif flt(advance.allocated_amount) == flt(allocated_amount):
                query = (
                    qb.from_(adv_type)
                    .delete()
                    .where(
                        (adv_type.parent == ref_doc.name)
                        & (adv_type.reference_name == payment_name)
                    )
                )
                query.run()


def unlink_ref_doc_from_payment_entries(
    ref_doc: object = None, payment_name: str | None = None, allocated_amount=None
):
    remove_ref_doc_link_from_jv(ref_doc.doctype, ref_doc.name, payment_name)
    remove_ref_doc_link_from_pe(ref_doc.doctype, ref_doc.name, payment_name)
    update_accounting_ledgers_after_reference_removal(ref_doc.doctype, ref_doc.name, payment_name)
    remove_ref_from_advance_section(ref_doc, payment_name, allocated_amount)
