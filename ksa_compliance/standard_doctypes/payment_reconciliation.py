import frappe
from erpnext.accounts.utils import get_outstanding_invoices
from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import PaymentReconciliation
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import is_advance_payment_invoice


class CustomPaymentReconciliation(PaymentReconciliation):
    def get_payment_entry_conditions(self):
        conditions = super().get_payment_entry_conditions()
        if self.party_type == "Customer":
            pe = frappe.qb.DocType("Payment Entry")
            conditions.append(pe.is_advance_payment == 0)
        return conditions

    def get_invoice_entries(self):
        # Fetch JVs, Sales and Purchase Invoices for 'invoices' to reconcile against

        self.build_qb_filter_conditions(get_invoices=True)

        non_reconciled_invoices = get_outstanding_invoices(
            self.party_type,
            self.party,
            self.receivable_payable_account,
            common_filter=self.common_filter_conditions,
            posting_date=self.ple_posting_date_filter,
            min_outstanding=self.minimum_invoice_amount if self.minimum_invoice_amount else None,
            max_outstanding=self.maximum_invoice_amount if self.maximum_invoice_amount else None,
            accounting_dimensions=self.accounting_dimension_filter_conditions,
            limit=self.invoice_limit,
            voucher_no=self.invoice_name,
        )

        cr_dr_notes = (
            [x.voucher_no for x in self.return_invoices]
            if self.party_type in ["Customer", "Supplier"]
            else []
        )
        # Filter out cr/dr notes from outstanding invoices list
        # Happens when non-standalone cr/dr notes are linked with another invoice through journal entry
        settings = ZATCABusinessSettings.for_company(self.company)
        filtered_non_reconciled_invoices = []
        for invoice in non_reconciled_invoices:
            if invoice.voucher_no in cr_dr_notes:
                continue
            invoice_doc = frappe.get_doc(invoice.voucher_type, invoice.voucher_no)
            if is_advance_payment_invoice(invoice_doc, settings) and not invoice_doc.is_return:
                continue
            filtered_non_reconciled_invoices.append(invoice)

        if self.invoice_limit:
            filtered_non_reconciled_invoices = filtered_non_reconciled_invoices[: self.invoice_limit]

        self.add_invoice_entries(filtered_non_reconciled_invoices)
