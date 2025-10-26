import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.accounts.utils import reconcile_against_document
from frappe.utils import flt

from ksa_compliance.standard_doctypes.sales_invoice_advance import (
    get_invoice_advance_payments,
    set_advance_payment_invoice_settling_gl_entries,
)
from ksa_compliance.standard_doctypes.unreconcile_payment import unreconcile_from_advance_payment
from ksa_compliance.zatca_guard import is_zatca_enabled


def get_return_against_advance_payments(return_against, grand_total):
    if not is_zatca_enabled():
        return []
    
    return_against_advance_payments = get_invoice_advance_payments(return_against)
    return_advance_payments = []
    return_allocated = 0
    for return_against_advance_payment in return_against_advance_payments:
        amount = grand_total
        allocated_amount = min(
            amount - return_allocated, return_against_advance_payment.allocated_amount
        )
        if allocated_amount == 0:
            break
        return_allocated += flt(allocated_amount)
        return_advance_payment = return_against_advance_payment.copy()
        return_advance_payment.allocated_amount = allocated_amount
        return_advance_payments.append(return_advance_payment)

    return return_advance_payments


def settle_return_invoice_paid_from_advance_payment(self):
    """
    Steps:
    1. Get advance payments allocated to the original (return_against) invoice.
    2. Create GL entries to reflect settlement for the advance invoice.
    3. Unreconcile the advance payment from the Payment Entry.
    4. Create GL entries for settlement for the return_against invoice.
    5. Reconcile any difference in allocated amounts.
    """
    if not is_zatca_enabled():
        return
    
    return_against = frappe.get_doc(self.doctype, self.return_against)
    return_against_advance_payments = get_return_against_advance_payments(
        return_against, abs(self.get("grand_total"))
    )

    for return_against_advance_payment in return_against_advance_payments:
        allocated_amount = return_against_advance_payment.allocated_amount

        # Create GL entries to reflect settlement for the advance invoice.
        set_advance_payment_invoice_settling_gl_entries(
            frappe._dict(
                allocated_amount=allocated_amount,
                reference_name=self.name,
                advance_payment_invoice=return_against_advance_payment.advance_payment_invoice,
            ),
            True,
        )

        reference_allocated_amount = frappe.get_value(
            "Payment Entry Reference",
            {
                "parent": return_against_advance_payment.reference_name,
                "reference_name": self.return_against,
            },
            "allocated_amount",
        )

        # Unreconcile Advance Invoice from Payment Entry After paid from gls
        unreconcile_from_advance_payment(
            company=self.company,
            voucher_type="Payment Entry",
            voucher_no=return_against_advance_payment.reference_name,
            against_voucher_type="Sales Invoice",
            against_voucher_no=self.return_against,
            allocated_amount=allocated_amount,
        )

        # Create GL entries for settlement for the return_against invoice.
        set_advance_payment_invoice_settling_gl_entries(
            frappe._dict(
                allocated_amount=allocated_amount,
                reference_name=self.name,
                advance_payment_invoice=self.return_against,
            )
        )

        # Reconcile any difference in allocated amounts.
        if reference_allocated_amount != allocated_amount:
            build_reconcile_against_document(
                return_against,
                return_against_advance_payment,
                round(abs(reference_allocated_amount - allocated_amount), 2),
            )


def build_reconcile_against_document(
    return_against, return_against_advance_payment, allocated_amount
):
    lst = []
    args = frappe._dict(
        {
            "voucher_type": "Payment Entry",
            "voucher_no": return_against_advance_payment.reference_name,
            "voucher_detail_no": return_against_advance_payment.reference_row,
            "against_voucher_type": return_against.doctype,
            "against_voucher": return_against.name,
            "account": return_against.debit_to,
            "party_type": "Customer",
            "party": return_against.customer,
            "is_advance": "Yes",
            "dr_or_cr": "credit_in_account_currency",
            "unadjusted_amount": flt(return_against_advance_payment.advance_amount),
            "allocated_amount": flt(allocated_amount),
            # "precision": return_against.precision("advance_amount"),
            "exchange_rate": (
                return_against.conversion_rate
                if return_against.party_account_currency != return_against.company_currency
                else 1
            ),
            "grand_total": (
                return_against.base_grand_total
                if return_against.party_account_currency == return_against.company_currency
                else return_against.grand_total
            ),
            "outstanding_amount": return_against.outstanding_amount,
            "difference_account": frappe.get_cached_value(
                "Company", return_against.company, "exchange_gain_loss_account"
            ),
            "exchange_gain_loss": flt(return_against_advance_payment.get("exchange_gain_loss")),
            "difference_posting_date": return_against_advance_payment.get(
                "difference_posting_date"
            ),
        }
    )
    lst.append(args)

    active_dimensions = get_dimensions()[0]
    for x in lst:
        for dim in active_dimensions:
            if return_against.get(dim.fieldname):
                x.update({dim.fieldname: return_against.get(dim.fieldname)})
    reconcile_against_document(lst, active_dimensions=active_dimensions)
