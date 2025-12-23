import base64
import datetime
from base64 import b64encode
from io import BytesIO
from typing import Optional, cast

import frappe
import pyqrcode
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry
from erpnext.setup.doctype.branch.branch import Branch
from frappe.utils import flt
from frappe.utils.data import get_time, getdate

from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
    ZATCABusinessSettings,
)
from ksa_compliance.standard_doctypes.sales_invoice_advance import get_prepayment_info
from ksa_compliance.utils.advance_payment_entry_taxes_and_charges import get_taxes_and_charges
from ksa_compliance.utils.update_itemised_tax_data import (
    calculate_net_from_gross_included_in_print_rate,
    calculate_tax_amount_included_in_print_rate,
)


def get_zatca_phase_1_qr_for_invoice(invoice_name: str) -> str:
    values = get_qr_inputs(invoice_name)
    if values is None:
        return values
    decoded_string = generate_decoded_string(values)
    return generate_qrcode(decoded_string)


def get_qr_inputs(invoice_name: str) -> list:
    invoice_doc: Optional[SalesInvoice] = None
    if frappe.db.exists("POS Invoice", invoice_name):
        invoice_doc = cast(POSInvoice, frappe.get_doc("POS Invoice", invoice_name))
    elif frappe.db.exists("Sales Invoice", invoice_name):
        invoice_doc = cast(SalesInvoice, frappe.get_doc("Sales Invoice", invoice_name))
    else:
        return None
    seller_name = invoice_doc.company
    phase_1_name = frappe.get_value("ZATCA Phase 1 Business Settings", {"company": seller_name})
    if not phase_1_name:
        return None
    phase_1_settings = frappe.get_doc("ZATCA Phase 1 Business Settings", phase_1_name)
    if phase_1_settings.status == "Disabled":
        return None
    seller_vat_reg_no = phase_1_settings.vat_registration_number
    time = invoice_doc.posting_time
    timestamp = format_date(invoice_doc.posting_date, time)
    grand_total = invoice_doc.grand_total
    total_vat = invoice_doc.total_taxes_and_charges
    # returned values should be ordered based on ZATCA Qr Specifications
    return [seller_name, seller_vat_reg_no, timestamp, grand_total, total_vat]


def generate_decoded_string(values: list) -> str:
    encoded_text = ""
    for tag, value in enumerate(values, 1):
        encoded_text += encode_input(value, [tag])
    # Decode hex result string into base64 format
    return b64encode(bytes.fromhex(encoded_text)).decode()


def encode_input(input: str, tag: int) -> str:
    """
    1- Convert bytes of tag into hex format.
    2- Convert bytes of encoded length of input into hex format.
    3- Convert encoded input itself into hex format.
    4- Concat All values into one string.
    """
    encoded_tag = bytes(tag).hex()
    if type(input) is str:
        encoded_length = bytes([len(input.encode("utf-8"))]).hex()
        encoded_value = input.encode("utf-8").hex()
    else:
        encoded_length = bytes([len(str(input).encode("utf-8"))]).hex()
        encoded_value = str(input).encode("utf-8").hex()
    return encoded_tag + encoded_length + encoded_value


def format_date(date: str, time: str) -> str:
    """
    Format date & time into UTC format something like : " 2021-12-13T10:39:15Z"
    """
    posting_date = getdate(date)
    time = get_time(time)
    combined_datetime = datetime.datetime.combine(posting_date, time)
    combined_utc = combined_datetime.astimezone(datetime.timezone.utc)
    time_stamp = combined_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return time_stamp


def generate_qrcode(data: str) -> str:
    if not data:
        return None
    qr = pyqrcode.create(data)
    with BytesIO() as buffer:
        qr.png(buffer, scale=7)
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return img_str


def get_advance_payment_entry_info(payment_entry, settings):
    taxes_and_charges = get_taxes_and_charges(payment_entry)
    tax_rate = taxes_and_charges.taxes[0].rate
    precision = payment_entry.precision("paid_amount")
    amount = flt(payment_entry.paid_amount, precision)
    net_amount = flt(calculate_net_from_gross_included_in_print_rate(amount, tax_rate), precision)
    tax_amount = flt(
        flt(calculate_tax_amount_included_in_print_rate(amount, net_amount)), precision
    )
    advance_payment_item = frappe.get_doc("Item", settings.advance_payment_item)
    return frappe._dict(
        {
            "item_name": advance_payment_item.item_name,
            "item_code": advance_payment_item.item_code,
            "amount": amount,
            "tax_rate": tax_rate,
            "net_amount": net_amount,
            "tax_amount": tax_amount,
        }
    )


def get_phase_2_print_format_details(
    sales_invoice: SalesInvoice | POSInvoice | PaymentEntry | JournalEntry,
) -> dict | None:
    settings_id = frappe.db.exists(
        "ZATCA Business Settings",
        {"company": sales_invoice.company, "enable_zatca_integration": True},
    )
    if not settings_id:
        return None

    branch_doc = None
    has_branch_address = False
    settings = cast(ZATCABusinessSettings, frappe.get_doc("ZATCA Business Settings", settings_id))
    if settings.enable_branch_configuration:
        if sales_invoice.branch:
            branch_doc = cast(Branch, frappe.get_doc("Branch", sales_invoice.branch))
            if branch_doc.custom_company_address:
                has_branch_address = True
    seller_other_id, seller_other_id_name = get_seller_other_id(sales_invoice, settings)
    advance_payment_entry = None
    if sales_invoice.doctype == "Payment Entry":
        customer = sales_invoice.party
        advance_payment_entry = get_advance_payment_entry_info(sales_invoice, settings)
        customer_id = sales_invoice.party
    elif sales_invoice.doctype == "Journal Entry":
        advance_payment_name = sales_invoice.advance_payment_entry
        if advance_payment_name:
            payment_entry = frappe.get_doc("Payment Entry", advance_payment_name)
            customer = payment_entry.party
        else:
            customer = None
        payment_entry = frappe.get_doc("Payment Entry", sales_invoice.advance_payment_entry)
        advance_payment_entry = get_advance_payment_entry_info(payment_entry, settings)
        customer_id = payment_entry.party
        net_amount =calculate_net_from_gross_included_in_print_rate(
            sales_invoice.accounts[0].debit_in_account_currency,
            advance_payment_entry.tax_rate,
        )
        tax_amount = calculate_tax_amount_included_in_print_rate(
            sales_invoice.accounts[0].debit_in_account_currency,
            net_amount,
        )    
    else:
        customer = sales_invoice.customer
        customer_id = getattr(sales_invoice, "customer", None)
    buyer_other_id, buyer_other_id_name = get_buyer_other_id(customer)
    siaf = frappe.get_last_doc(
        "Sales Invoice Additional Fields", {"sales_invoice": sales_invoice.name}
    )
    prepayment_info = get_prepayment_info(sales_invoice)
    if advance_payment_entry:
        advance_payment_entry.party = customer_id
    return {
        "settings": settings,
        "address": {
            "street": branch_doc.custom_street if has_branch_address else settings.street,
            "district": branch_doc.custom_district if has_branch_address else settings.district,
            "city": branch_doc.custom_city if has_branch_address else settings.city,
            "postal_code": (
                branch_doc.custom_postal_code if has_branch_address else settings.postal_code
            ),
        },
        "seller_other_id": seller_other_id,
        "seller_other_id_name": seller_other_id_name,
        "buyer_other_id": buyer_other_id,
        "buyer_other_id_name": buyer_other_id_name,
        "siaf": siaf,
        "prepayment_info": prepayment_info,
        "advance_payment_entry": advance_payment_entry,
        "net_amount": net_amount,
        "tax_amount": tax_amount,
    }


def get_seller_other_id(
    sales_invoice: SalesInvoice | POSInvoice, settings: ZATCABusinessSettings
) -> tuple:
    seller_other_ids = ["CRN", "MOM", "MLS", "700", "SAG", "OTH"]
    seller_other_id, seller_other_id_name = None, None
    if settings.enable_branch_configuration:
        if sales_invoice.branch:
            seller_other_id = frappe.get_value(
                "Additional Seller IDs",
                {"parent": sales_invoice.branch, "type_code": "CRN"},
                "value",
            )
    if not seller_other_id:
        for other_id in seller_other_ids:
            seller_other_id = frappe.get_value(
                "Additional Seller IDs", {"parent": settings.name, "type_code": other_id}, "value"
            )
            seller_other_id = (
                seller_other_id.strip() or None
                if isinstance(seller_other_id, str)
                else seller_other_id
            )
            if seller_other_id and seller_other_id != "CRN":
                seller_other_id_name = frappe.get_value(
                    "Additional Seller IDs",
                    {"parent": settings.name, "type_code": other_id},
                    "type_name",
                )
                break
    return seller_other_id, seller_other_id_name or "Commercial Registration Number"


def get_buyer_other_id(customer: str) -> tuple:
    buyer_other_ids = ["TIN", "CRN", "MOM", "MLS", "700", "SAG", "NAT", "GCC", "IQA", "PAS", "OTH"]
    buyer_other_id, buyer_other_id_name = None, None
    for other_id in buyer_other_ids:
        buyer_other_id = frappe.get_value(
            "Additional Buyer IDs", {"parent": customer, "type_code": other_id}, "value"
        )
        buyer_other_id = (
            buyer_other_id.strip() or None if isinstance(buyer_other_id, str) else buyer_other_id
        )
        if buyer_other_id and buyer_other_id != "CRN":
            buyer_other_id_name = frappe.get_value(
                "Additional Buyer IDs", {"parent": customer, "type_code": other_id}, "type_name"
            )
            break
    return buyer_other_id, buyer_other_id_name or "Commercial Registration Number"
