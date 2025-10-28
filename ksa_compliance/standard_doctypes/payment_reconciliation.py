import frappe
from erpnext.accounts.doctype.payment_reconciliation.payment_reconciliation import (
    PaymentReconciliation,
)
from erpnext.accounts.utils import get_outstanding_invoices
from frappe import qb
from frappe.query_builder import Criterion
from frappe.query_builder.custom import ConstantColumn

from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
    ZATCABusinessSettings,
)
from ksa_compliance.standard_doctypes.sales_invoice_advance import (
    get_advance_payment_query_condition,
)
from ksa_compliance.utils.advance_payment_invoice import invoice_has_advance_item
from ksa_compliance.zatca_guard import is_zatca_enabled


class CustomPaymentReconciliation(PaymentReconciliation):

    def get_payment_entries(self):
        """
        HANDLE CHANGING ON LOGIC ON GETTING PAYMENT ENTRIES BETWEEN VERSION 14 AND 15
        """
        if not is_zatca_enabled(self.company):
            return super().get_payment_entries()
        frappe_version = frappe.__version__
        if self.party_type == "Customer" and frappe_version.startswith("15"):
            return self.get_non_advance_payment_entries()
        return super().get_payment_entries()

    def get_non_advance_payment_entries(self):
        settings = ZATCABusinessSettings.for_company(self.company)
        if getattr(settings, "enable_zatca_integration", False):
            return super().get_payment_entries()
        payment_entries = super().get_payment_entries()
        if not payment_entries:
            return []
        payment_entry_names = [payment_entry.reference_name for payment_entry in payment_entries]
        payment_entry = frappe.qb.DocType("Payment Entry")
        advance_payment_query_condition = get_advance_payment_query_condition(
            payment_entry, settings.advance_payment_depends_on
        )
        advance_payment_entries = (
            frappe.qb.from_(payment_entry)
            .select(payment_entry.name)
            .where(
                advance_payment_query_condition & (payment_entry.name.isin(payment_entry_names))
            )
        ).run(pluck=True)
        if not advance_payment_entries:
            return payment_entries
        return [pe for pe in payment_entries if pe.reference_name not in advance_payment_entries]

    def get_payment_entry_conditions(self):
        settings = ZATCABusinessSettings.for_company(self.company)
        if getattr(settings, "enable_zatca_integration", False):
            return super().get_payment_entry_conditions()
        conditions = super().get_payment_entry_conditions()
        if self.party_type == "Customer":
            pe = frappe.qb.DocType("Payment Entry")
            advance_payment_query_condition = get_advance_payment_query_condition(
                pe, settings.advance_payment_depends_on, reverse=True
            )
            conditions.append(advance_payment_query_condition)
        return conditions

    def get_invoice_entries(self):
        settings = ZATCABusinessSettings.for_company(self.company)
        if getattr(settings, "enable_zatca_integration", False):
            return super().get_invoice_entries()
        frappe_version = frappe.__version__
        # Fetch JVs, Sales and Purchase Invoices for 'invoices' to reconcile against

        self.build_qb_filter_conditions(get_invoices=True)

        non_reconciled_invoices = get_outstanding_invoices(
            self.party_type,
            self.party,
            (
                self.receivable_payable_account
                if frappe_version.startswith("14")
                else [self.receivable_payable_account]
            ),
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
        filtered_non_reconciled_invoices = []
        for invoice in non_reconciled_invoices:
            if invoice.voucher_no in cr_dr_notes:
                continue
            if invoice.voucher_type == "Sales Invoice":
                invoice_doc = frappe.get_doc(invoice.voucher_type, invoice.voucher_no)
                if invoice_has_advance_item(invoice_doc, settings):
                    continue
            filtered_non_reconciled_invoices.append(invoice)

        if self.invoice_limit:
            filtered_non_reconciled_invoices = filtered_non_reconciled_invoices[
                : self.invoice_limit
            ]

        self.add_invoice_entries(filtered_non_reconciled_invoices)

    def get_return_invoices(self):
        settings = ZATCABusinessSettings.for_company(self.company)
        if getattr(settings, "enable_zatca_integration", False):
            return super().get_return_invoices()
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
            sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
            siap = qb.DocType("Sales Invoice Advance Payment")

            self.return_invoices_query = (
                self.return_invoices_query.join(sales_invoice_item)
                .on(sales_invoice_item.parent == doc.name)
                .left_join(siap)
                .on(siap.parent == doc.name)
            )
            self.return_invoices_query = self.return_invoices_query.where(
                (sales_invoice_item.item_code != settings.advance_payment_item)
                & (siap.name.isnull())
            )

        if self.payment_limit:
            self.return_invoices_query = self.return_invoices_query.limit(self.payment_limit)

        self.return_invoices = self.return_invoices_query.run(as_dict=True)
