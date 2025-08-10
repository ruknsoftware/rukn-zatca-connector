import frappe
from frappe import qb
from frappe.query_builder import Criterion
from frappe.query_builder.custom import ConstantColumn
from erpnext.accounts.utils import get_outstanding_invoices
from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import PaymentReconciliation
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.utils.advance_payment_invoice import invoice_has_advance_item


class CustomPaymentReconciliation(PaymentReconciliation):
    def get_payment_entry_conditions(self):
        conditions = super().get_payment_entry_conditions()
        if self.party_type == "Customer":
            pe = frappe.qb.DocType("Payment Entry")
            conditions.append(pe.is_advance_payment == 0)
        return conditions

    def get_invoice_entries(self):
        frappe_version = frappe.__version__
        # Fetch JVs, Sales and Purchase Invoices for 'invoices' to reconcile against

        self.build_qb_filter_conditions(get_invoices=True)

        non_reconciled_invoices = get_outstanding_invoices(
            self.party_type,
            self.party,
            self.receivable_payable_account if frappe_version.startswith("14") else [self.receivable_payable_account],
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
            if invoice_has_advance_item(invoice_doc, settings):
                continue
            filtered_non_reconciled_invoices.append(invoice)

        if self.invoice_limit:
            filtered_non_reconciled_invoices = filtered_non_reconciled_invoices[: self.invoice_limit]

        self.add_invoice_entries(filtered_non_reconciled_invoices)

    def get_return_invoices(self):
        voucher_type = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"
        doc = qb.DocType(voucher_type)

        conditions = []
        conditions.append(doc.docstatus == 1)
        conditions.append(doc[frappe.scrub(self.party_type)] == self.party)
        conditions.append(doc.is_return == 1)
        conditions.append(doc.outstanding_amount != 0)

        if self.payment_name:
            conditions.append(doc.name.like(f"%{self.payment_name}%"))

        self.return_invoices_query = (
            qb.from_(doc)
            .select(
                ConstantColumn(voucher_type).as_("voucher_type"),
                doc.name.as_("voucher_no"),
                doc.return_against,
            )
            .where(Criterion.all(conditions))
        )
        if voucher_type == "Sales Invoice":
            settings = ZATCABusinessSettings.for_company(self.company)
            sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
            self.return_invoices_query = self.return_invoices_query.join(sales_invoice_item).on(
                sales_invoice_item.parent == doc.name)
            self.return_invoices_query = self.return_invoices_query.where(
                sales_invoice_item.item_code != settings.advance_payment_item)

        if self.payment_limit:
            self.return_invoices_query = self.return_invoices_query.limit(self.payment_limit)

        self.return_invoices = self.return_invoices_query.run(as_dict=True)
