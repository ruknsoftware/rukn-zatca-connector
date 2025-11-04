from datetime import date

import frappe
import frappe.utils.background_jobs
from erpnext.accounts.doctype.account.account import get_account_currency
from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry
from erpnext.accounts.doctype.payment_entry.payment_entry import (
    PaymentEntry,
    get_account_details,
    get_party_details,
    set_grand_total_and_outstanding_amount,
)
from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
    SalesInvoice,
    get_bank_cash_account,
)
from erpnext.accounts.utils import get_balance_on
from erpnext.setup.utils import get_exchange_rate
from frappe import _
from frappe.utils import cint, flt, strip
from result import is_ok

from ksa_compliance import logger
from ksa_compliance.invoice import InvoiceMode
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    SalesInvoiceAdditionalFields,
)
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
    ZATCABusinessSettings,
)
from ksa_compliance.ksa_compliance.doctype.zatca_egs.zatca_egs import ZATCAEGS
from ksa_compliance.ksa_compliance.doctype.zatca_phase_1_business_settings.zatca_phase_1_business_settings import (
    ZATCAPhase1BusinessSettings,
)
from ksa_compliance.ksa_compliance.doctype.zatca_precomputed_invoice.zatca_precomputed_invoice import (
    ZATCAPrecomputedInvoice,
)
from ksa_compliance.standard_doctypes.payment_entry import (
    set_advance_payment_entry_settling_references,
)
from ksa_compliance.standard_doctypes.sales_invoice_advance import (
    calculate_advance_payment_tax_amount,
    get_invoice_advance_payments,
    get_invoice_applicable_advance_payments,
    is_advance_payment_condition,
    set_advance_payment_invoice_settling_gl_entries,
)
from ksa_compliance.translation import ft
from ksa_compliance.utils.advance_payment_entry_taxes_and_charges import get_taxes_and_charges
from ksa_compliance.utils.advance_payment_invoice import invoice_has_advance_item
from ksa_compliance.utils.return_invoice_paid_from_advance_payment import (
    get_return_against_advance_payments,
    settle_return_invoice_paid_from_advance_payment,
    update_advance_payment_tax_allocation,
)

IGNORED_INVOICES = set()


def ignore_additional_fields_for_invoice(name: str) -> None:
    IGNORED_INVOICES.add(name)


def clear_additional_fields_ignore_list() -> None:
    IGNORED_INVOICES.clear()


def create_sales_invoice_additional_fields_doctype(
    self: SalesInvoice | POSInvoice | PaymentEntry | JournalEntry, method
):
    settings = ZATCABusinessSettings.for_invoice(self.name, self.doctype)
    if not getattr(settings, "enable_zatca_integration", False):
        return
    if self.doctype == "Sales Invoice" and not _should_enable_zatca_for_invoice(self.name):
        logger.info(f"Skipping additional fields for {self.name} because it's before start date")
        return

    if not settings:
        logger.info(
            f"Skipping additional fields for {self.name} because of missing ZATCA settings"
        )
        return

    if not getattr(settings, "enable_zatca_integration", False):
        logger.info(
            f"Skipping additional fields for {self.name} because ZATCA integration is disabled in settings"
        )
        return

    if self.name in IGNORED_INVOICES:
        logger.info(f"Skipping additional fields for {self.name} because it's in the ignore list")
        return

    if self.doctype == "Sales Invoice" and self.is_consolidated:
        logger.info(f"Skipping additional fields for {self.name} because it's consolidated")
        return
    if self.doctype == "Payment Entry" and not self.is_advance_payment_depends_on_entry:
        return
    if self.doctype == "Journal Entry" and not self.advance_payment_entry:
        return

    si_additional_fields_doc = SalesInvoiceAdditionalFields.create_for_invoice(
        self.name, self.doctype
    )
    precomputed_invoice = ZATCAPrecomputedInvoice.for_invoice(self.name)
    is_live_sync = settings.is_live_sync
    if precomputed_invoice:
        logger.info(f"Using precomputed invoice {precomputed_invoice.name} for {self.name}")
        si_additional_fields_doc.use_precomputed_invoice(precomputed_invoice)

        egs_settings = ZATCAEGS.for_device(precomputed_invoice.device_id)
        if not egs_settings:
            logger.warning(f"Could not find EGS for device {precomputed_invoice.device_id}")
        else:
            # EGS Setting overrides company-wide setting
            is_live_sync = egs_settings.is_live_sync

    si_additional_fields_doc.insert()
    if self.doctype in ("Sales Invoice", "POS Invoice"):
        is_advance_invoice = invoice_has_advance_item(self, settings)
        if is_advance_invoice:
            payment_entry = create_payment_entry_for_advance_payment_invoice(self)
            if self.is_return:
                advance_payment = frappe._dict(
                    allocated_amount=abs(self.grand_total),
                    reference_name=self.name,
                    advance_payment_invoice=self.return_against,
                )
                set_advance_payment_invoice_settling_gl_entries(advance_payment)
                set_advance_payment_entry_settling_references(payment_entry)
        if self.is_return:
            if not is_advance_invoice:
                settle_return_invoice_paid_from_advance_payment(self, settings)
        else:
            if settings.advance_payment_depends_on == "Sales Invoice":
                advance_payments = get_invoice_advance_payments(self)
                for advance_payment in advance_payments:
                    set_advance_payment_invoice_settling_gl_entries(advance_payment)

    if is_live_sync:
        # We're running in the context of invoice submission (on_submit hook). We only want to run our ZATCA logic if
        # the invoice submits successfully after on_submit is run successfully from all apps.
        frappe.utils.background_jobs.enqueue(
            _submit_additional_fields, doc=si_additional_fields_doc, enqueue_after_commit=True
        )


def _submit_additional_fields(doc: SalesInvoiceAdditionalFields):
    logger.info(f"Submitting {doc.name}")
    result = doc.submit_to_zatca()
    message = result.ok_value if is_ok(result) else result.err_value
    logger.info(f"Submission result: {message}")


def _should_enable_zatca_for_invoice(invoice_id: str) -> bool:
    start_date = date(2024, 3, 1)

    if frappe.db.table_exists("Vehicle Booking Item Info"):
        # noinspection SqlResolve
        records = frappe.db.sql(
            "SELECT bv.local_trx_date_time FROM `tabVehicle Booking Item Info` bvii "
            "JOIN `tabBooking Vehicle` bv ON bvii.parent = bv.name WHERE bvii.sales_invoice = %(invoice)s",
            {"invoice": invoice_id},
            as_dict=True,
        )
        if records:
            local_date = records[0]["local_trx_date_time"].date()
            return local_date >= start_date

    posting_date = frappe.db.get_value("Sales Invoice", invoice_id, "posting_date")
    return posting_date >= start_date


def prevent_cancellation_of_sales_invoice(
    self: SalesInvoice | POSInvoice | PaymentEntry | JournalEntry, method
) -> None:
    settings = ZATCABusinessSettings.for_invoice(self.name, self.doctype)
    if not settings or not getattr(settings, "enable_zatca_integration", False):
        return
    is_phase_2_enabled_for_company = settings.enable_zatca_integration
    if is_phase_2_enabled_for_company:
        if self.doctype == "Payment Entry":
            is_advance_payment = is_advance_payment_condition(
                self, settings.advance_payment_depends_on
            )
            if not is_advance_payment:
                return
            frappe.throw(
                msg=_(
                    "You cannot cancel {0} according to ZATCA Advance Invoice {1}.",
                ).format(
                    self.name,
                    frappe.utils.get_link_to_form(
                        self.invoice_doctype, self.advance_payment_invoice
                    ),
                ),
                title=_("This Action Is Not Allowed"),
            )
        if self.doctype == "Journal Entry" and self.advance_payment_entry:
            frappe.throw(
                msg=_(
                    "You cannot cancel {0} according to ZATCA Advance Invoice {1}.",
                ).format(
                    self.name,
                    frappe.utils.get_link_to_form("Payment Entry", self.advance_payment_entry),
                ),
                title=_("This Action Is Not Allowed"),
            )
        frappe.throw(
            msg=_(
                "You cannot cancel {0} according to ZATCA Regulations.",
            ).format(self.doctype),
            title=_("This Action Is Not Allowed"),
        )


def validate_sales_invoice(self: SalesInvoice | POSInvoice, method) -> None:
    settings = ZATCABusinessSettings.for_company(self.company)
    if not settings or not getattr(settings, "enable_zatca_integration", False):
        return
    valid = True
    is_phase_2_enabled_for_company = ZATCABusinessSettings.is_enabled_for_company(self.company)
    if (
        ZATCAPhase1BusinessSettings.is_enabled_for_company(self.company)
        or is_phase_2_enabled_for_company
    ):
        if len(self.taxes) == 0:
            frappe.msgprint(
                msg=_("Please include tax rate in Sales Taxes and Charges Table"),
                title=_("Validation Error"),
                indicator="red",
            )
            valid = False

    if is_phase_2_enabled_for_company:

        is_advance_invoice = invoice_has_advance_item(self, settings)
        valid_advance_payment_invoice = is_valid_advance_invoice(is_advance_invoice, self)
        if not valid_advance_payment_invoice:
            frappe.msgprint(
                msg=_("Advance payment invoices must include only the advance payment item"),
                title=_("Validation Error"),
                indicator="red",
                raise_exception=True,
            )
            valid = False
        elif is_advance_invoice and self.advances:
            frappe.msgprint(
                msg=_("Advance payment invoices can not include Advance Payments"),
                title=_("Validation Error"),
                indicator="red",
                raise_exception=True,
            )
            valid = False

        advance_payments = get_invoice_advance_payments(self)
        if self.is_return:
            return_against = frappe.get_doc(self.doctype, self.return_against)
            advance_payments = get_return_against_advance_payments(
                return_against, abs(self.get("grand_total"))
            )
            if (is_advance_invoice or advance_payments) and abs(
                self.grand_total
            ) > return_against.outstanding_amount:
                frappe.msgprint(
                    _("Cant Return exceeds the outstanding amount {0} of Advance Invoice").format(
                        return_against.outstanding_amount
                    ),
                    title=_("Validation Error"),
                    indicator="red",
                )
                valid = False

        self.advance_payment_invoices = []
        if advance_payments:
            if self.doctype == "POS Invoice":
                frappe.msgprint(
                    msg=_("Cant Add Advance Payments Invoices Entries On POS Invoice"),
                    title=_("Validation Error"),
                    indicator="red",
                    raise_exception=True,
                )
                valid = False
            else:
                for advance_payment in advance_payments:
                    advance_payment_invoice = advance_payment.copy()

                    if settings.advance_payment_depends_on == "Sales Invoice":
                        advance_payment_invoice.reference_type = "Sales Invoice"
                        advance_payment_invoice.reference_name = (
                            advance_payment.advance_payment_invoice
                        )
                        advance_payment_invoice_doc = frappe.get_doc(
                            "Sales Invoice", advance_payment.advance_payment_invoice
                        )
                        item = advance_payment_invoice_doc.items[0]
                        tax_percent = abs(item.tax_rate or 0.0)
                        tax_amount = calculate_advance_payment_tax_amount(
                            advance_payment_invoice, advance_payment_invoice_doc
                        )
                        advance_payment_invoice.tax_percent = tax_percent
                        advance_payment_invoice.tax_amount = tax_amount
                    else:
                        advance_payment_invoice.reference_type = "Payment Entry"
                        advance_payment_invoice.reference_name = advance_payment.reference_name
                        advance_payment_invoice_doc = frappe.get_doc(
                            "Payment Entry", advance_payment.reference_name
                        )
                        taxes_and_charges = get_taxes_and_charges(advance_payment_invoice_doc)
                        tax_percent = taxes_and_charges.taxes[0].rate
                        tax_amount = calculate_advance_payment_tax_amount(
                            advance_payment,
                            self,
                            settings.advance_payment_depends_on,
                        )
                        advance_payment_invoice.tax_percent = tax_percent
                        advance_payment_invoice.tax_amount = tax_amount
                        advance_payment_invoice.allocated_tax = tax_amount
                        advance_payment_invoice.unallocated_tax = 0.0

                    self.append("advance_payment_invoices", advance_payment_invoice)

        validate_customer_vat_compliance(self, method)

    if not valid:
        message_log = frappe.get_message_log()
        error_messages = "\n".join(log["message"] for log in message_log)
        raise frappe.ValidationError(error_messages)


def validate_customer_vat_compliance(self, method):
    settings = ZATCABusinessSettings.for_company(self.company)
    if not getattr(settings, "enable_zatca_integration", False):
        return
    if self.doctype == "Payment Entry" and self.party_type != "Customer":
        return

    customer_name = self.get("customer") or self.get("party")
    if not customer_name:
        return

    customer = frappe.get_doc("Customer", customer_name)
    is_customer_have_vat_number = customer.custom_vat_registration_number and not any(
        [strip(x.value) for x in customer.custom_additional_ids]
    )

    check_vat_number_on_standard_invoice_mode = (
        settings.invoice_mode == InvoiceMode.Standard and not is_customer_have_vat_number
    )

    check_vat_number_on_auto_invoice_mode = (
        settings.invoice_mode == InvoiceMode.Auto
        and customer.customer_type != "Individual"
        and not is_customer_have_vat_number
    )
    if check_vat_number_on_standard_invoice_mode or check_vat_number_on_auto_invoice_mode:
        frappe.throw(
            ft(
                "Company <b>$company</b> is configured to use Standard Tax Invoices, which require customers to "
                "define a VAT number or one of the other IDs. Please update customer <b>$customer</b>",
                company=self.company,
                customer=self.get("customer"),
            )
        )


def auto_apply_advance_payments(self: SalesInvoice, method):
    settings = ZATCABusinessSettings.for_company(self.company)
    if (
        not settings
        or not getattr(settings, "enable_zatca_integration", False)
        or not settings.auto_apply_advance_payments
    ):
        return

    applicable_advance_payments = get_invoice_applicable_advance_payments(self, is_validate=True)
    if len(applicable_advance_payments) != 0:
        self.advances = []
        self.extend("advances", applicable_advance_payments)


def is_valid_advance_invoice(is_advance_invoice, self) -> bool:
    if not is_advance_invoice:
        return True
    return len(self.items) == 1


def create_payment_entry_for_advance_payment_invoice(
    self: SalesInvoice | POSInvoice,
) -> PaymentEntry:
    payment_type = "Receive"
    advance_payment_invoice = self.name
    if self.is_return:
        payment_type = "Pay"
        advance_payment_invoice = self.return_against

    payment_entry = frappe.new_doc("Payment Entry")
    payment_entry.payment_type = payment_type
    payment_entry.posting_date = self.posting_date
    payment_entry.posting_time = self.posting_time
    payment_entry.company = self.company
    payment_entry.party_type = "Customer"
    payment_entry.party = self.customer
    payment_entry.cost_center = self.cost_center
    payment_entry.paid_amount = abs(self.grand_total)
    payment_entry.mode_of_payment = self.mode_of_payment
    payment_entry.reference_no = self.reference_no
    payment_entry.reference_date = self.reference_date

    payment_entry.is_advance_payment = True
    payment_entry.invoice_doctype = self.doctype
    payment_entry.advance_payment_invoice = advance_payment_invoice

    party_details = get_party_details(
        company=payment_entry.company,
        party_type="Customer",
        party=payment_entry.party,
        date=payment_entry.posting_date,
        cost_center=payment_entry.cost_center,
    )

    bank = self.mode_of_payment_account or get_bank_cash_account(
        mode_of_payment=payment_entry.mode_of_payment, company=payment_entry.company
    ).get("account")
    bank_account_currency = get_account_currency(bank)
    if payment_type == "Receive":
        payment_entry.paid_from = party_details.get("party_account")
        payment_entry.paid_from_account_currency = party_details.get("party_account_currency")
        payment_entry.paid_from_account_balance = party_details.get("account_balance")

        payment_entry.paid_to = bank
    else:
        payment_entry.paid_from = bank
        payment_entry.paid_from_account_currency = bank_account_currency
        payment_entry.paid_from_account_balance = get_balance_on(
            bank, self.posting_date, cost_center=payment_entry.cost_center
        )
        payment_entry.paid_to = party_details.get("party_account")

        grand_total, outstanding_amount = set_grand_total_and_outstanding_amount(
            self.grand_total, self.doctype, party_details.get("party_account_currency"), self
        )
        payment_entry.append(
            "references",
            {
                "reference_doctype": self.doctype,
                "reference_name": self.name,
                "bill_no": self.get("bill_no"),
                "due_date": self.get("due_date"),
                "total_amount": grand_total,
                "outstanding_amount": outstanding_amount,
                "allocated_amount": outstanding_amount,
            },
        )

    payment_entry.party_balance = party_details.get("party_balance")
    payment_entry.party_name = party_details.get("party_name")

    payment_entry.paid_from_account_type = frappe.db.get_value(
        "Account", payment_entry.paid_from, "account_type"
    )
    payment_entry.paid_to_account_type = frappe.db.get_value(
        "Account", payment_entry.paid_to, "account_type"
    )

    if party_details.get("bank_account"):
        payment_entry.bank_account = party_details.get("bank_account")

    if payment_entry.paid_from_account_currency:
        ex_rate_src = get_exchange_rate(
            transaction_date=payment_entry.posting_date,
            from_currency=payment_entry.paid_from_account_currency,
            to_currency=self.currency,
        )
        precision = payment_entry.meta.get_field("source_exchange_rate").precision
        payment_entry.source_exchange_rate = flt(ex_rate_src, precision)

    if self.posting_date and payment_entry.paid_to:
        account_details = get_account_details(
            account=payment_entry.paid_to,
            date=payment_entry.posting_date,
            cost_center=payment_entry.cost_center,
        )
        payment_entry.paid_to_account_currency = account_details.get("account_currency")
        payment_entry.paid_to_account_balance = account_details.get("account_balance")

        if account_details.get("account_type") == "Bank":
            if not payment_entry.reference_no or not payment_entry.reference_date:
                frappe.throw(
                    _("Reference No and Reference Date are required for Bank accounts."),
                    exc=frappe.MandatoryError,
                )

        if payment_entry.paid_from_account_currency == payment_entry.paid_to_account_currency:
            payment_entry.target_exchange_rate = payment_entry.source_exchange_rate
            payment_entry.received_amount = payment_entry.paid_amount
        else:
            payment_entry.received_amount = flt(
                payment_entry.paid_amount * payment_entry.target_exchange_rate,
                payment_entry.meta.get_field("received_amount").precision,
            )

        if payment_entry.paid_to_account_currency:
            ex_rate = get_exchange_rate(
                transaction_date=payment_entry.posting_date,
                from_currency=payment_entry.paid_to_account_currency,
                to_currency=self.currency,
            )
            precision = payment_entry.meta.get_field("target_exchange_rate").precision
            payment_entry.target_exchange_rate = flt(ex_rate, precision)

    payment_entry.setup_party_account_field()
    payment_entry.set_missing_values()
    payment_entry.set_missing_ref_details()
    payment_entry.allocate_amount_to_references(
        paid_amount=payment_entry.paid_amount,
        paid_amount_change=True,
        allocate_payment_amount=True,
    )
    payment_entry.save()
    payment_entry.submit()
    return payment_entry


class AdvanceSalesInvoice(SalesInvoice):
    def make_tax_gl_entries(self, gl_entries):
        settings = ZATCABusinessSettings.for_invoice(self.name, self.doctype)
        if self.is_return:
            return_against = frappe.get_doc("Sales Invoice", self.return_against)
            advance_payments = get_return_against_advance_payments(
                return_against, abs(self.grand_total)
            )
        else:
            advance_payments = get_invoice_advance_payments(self)
        if (
            not advance_payments
            or not settings
            or settings.advance_payment_depends_on != "Payment Entry"
            or not getattr(settings, "enable_zatca_integration", False)
        ):
            return super().make_tax_gl_entries(gl_entries)

        enable_discount_accounting = cint(
            frappe.db.get_single_value("Selling Settings", "enable_discount_accounting")
        )

        total_advance_taxes_amount = 0

        for advance_payment in advance_payments:
            advance_payment_tax = calculate_advance_payment_tax_amount(
                advance_payment, self, settings.advance_payment_depends_on
            )
            total_advance_taxes_amount += abs(advance_payment_tax)

        advance_tax_account = settings.advance_payment_tax_account

        for tax in self.get("taxes"):
            amount, base_amount = self.get_tax_amounts(tax, enable_discount_accounting)
            if not flt(tax.base_tax_amount_after_discount_amount):
                continue

            account_currency = get_account_currency(tax.account_head)
            tax_amount = abs(flt(base_amount, tax.precision("tax_amount_after_discount_amount")))

            advance_tax_account_currency = get_account_currency(advance_tax_account)

            if advance_tax_account_currency != self.company_currency:
                frappe.throw(
                    _(
                        "Advance tax account currency ({0}) must match company currency ({1}). "
                        "Multi-currency handling for advance portion is not supported yet."
                    ).format(advance_tax_account_currency, self.company_currency)
                )
            if total_advance_taxes_amount > 0 and advance_tax_account:
                advance_portion = min(total_advance_taxes_amount, tax_amount)
                gl_entries.append(
                    self.get_gl_dict(
                        {
                            "account": advance_tax_account,
                            "against": self.customer,
                            "credit": advance_portion * -1 if self.is_return else advance_portion,
                            "credit_in_account_currency": (
                                advance_portion * -1 if self.is_return else advance_portion
                            ),
                            "cost_center": tax.cost_center,
                        },
                        account_currency,
                        item=tax,
                    )
                )

                total_advance_taxes_amount -= advance_portion
                tax_amount -= advance_portion

            if tax_amount > 0:

                gl_entries.append(
                    self.get_gl_dict(
                        {
                            "account": tax.account_head,
                            "against": self.customer,
                            "credit": tax_amount * -1 if self.is_return else tax_amount,
                            "credit_in_account_currency": (
                                tax_amount * -1
                                if self.is_return
                                else (
                                    tax_amount
                                    if account_currency == self.company_currency
                                    else flt(
                                        amount, tax.precision("tax_amount_after_discount_amount")
                                    )
                                )
                            ),
                            "cost_center": tax.cost_center,
                        },
                        account_currency,
                        item=tax,
                    )
                )


def update_advance_payment_entry_tax_allocation(self, method):
    settings = ZATCABusinessSettings.for_invoice(self.name, self.doctype)
    if not settings:
        logger.info(
            f"Skipping additional fields for {self.name} because of missing ZATCA settings"
        )
        return
    if self.is_return:
        return

    advance_payments = get_invoice_advance_payments(self)
    for advance_payment in advance_payments:
        update_advance_payment_tax_allocation(self, advance_payment, settings)
