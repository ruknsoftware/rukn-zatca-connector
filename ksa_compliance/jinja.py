import base64
import datetime
import json
from base64 import b64encode
from io import BytesIO
from typing import Any, Optional, cast

import erpnext
import frappe
import pyqrcode
from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from frappe import _dict
from frappe.utils import flt
from frappe.utils.data import get_time, getdate

from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
    ZATCABusinessSettings,
)
from ksa_compliance.utils.advance_payment_entry_taxes_and_charges import get_taxes_and_charges
from ksa_compliance.utils.update_itemised_tax_data import (
    calculate_net_from_gross_included_in_print_rate,
    calculate_tax_amount_included_in_print_rate,
)
from ksa_compliance.utils.xml_parser import parse_xml_to_dict


def get_zatca_phase_1_qr_for_invoice(invoice_name: str) -> str:
    values = get_qr_inputs(invoice_name)
    if values is None:
        return values
    decoded_string = generate_decoded_string(values)
    return generate_qrcode(decoded_string)


def _resolve_invoice_doc(
    invoice,
) -> "Optional[SalesInvoice | POSInvoice]":
    """Resolve an invoice name or doc object to a SalesInvoice/POSInvoice doc."""
    if not isinstance(invoice, str):
        return invoice
    if frappe.db.exists("POS Invoice", invoice):
        return cast(POSInvoice, frappe.get_doc("POS Invoice", invoice))
    if frappe.db.exists("Sales Invoice", invoice):
        return cast(SalesInvoice, frappe.get_doc("Sales Invoice", invoice))
    return None


def _get_zatca_phase1_settings(company: str):
    """Return enabled ZATCA Phase 1 Business Settings for a company, or None."""
    phase_1_name = frappe.get_value("ZATCA Phase 1 Business Settings", {"company": company})
    if not phase_1_name:
        return None
    phase_1_settings = frappe.get_doc("ZATCA Phase 1 Business Settings", phase_1_name)
    if phase_1_settings.status == "Disabled":
        return None
    return phase_1_settings


def get_qr_inputs(invoice_name: str) -> list | None:
    invoice_doc = _resolve_invoice_doc(invoice_name)
    if invoice_doc is None:
        return None
    seller_name = invoice_doc.company
    phase_1_settings = _get_zatca_phase1_settings(seller_name)
    if not phase_1_settings:
        return None
    seller_vat_reg_no = phase_1_settings.vat_registration_number
    time = invoice_doc.posting_time
    timestamp = format_date(invoice_doc.posting_date, time)
    grand_total = invoice_doc.grand_total
    total_vat = invoice_doc.total_taxes_and_charges
    # returned values should be ordered based on ZATCA Qr Specifications
    return [seller_name, seller_vat_reg_no, timestamp, grand_total, total_vat]


def get_item_tax_details(invoice, item_row) -> _dict[str, float | Any] | None:
    """Return tax details for a single invoice item row.

    Accepts either an invoice name (str) or a doc object — resolves POS Invoice
    and Sales Invoice via _resolve_invoice_doc, then validates ZATCA Phase 1
    Business Settings via _get_zatca_phase1_settings the same way get_qr_inputs does.

    In ERPNext v16, item_wise_tax_detail was removed from Sales Taxes and Charges.
    tax_rate and tax_amount are now always stored directly on the item row.
    For older documents where those fields are zero, we fall back to item_wise_tax_detail.
    """
    doc = _resolve_invoice_doc(invoice)
    if doc is None:
        return None

    if not _get_zatca_phase1_settings(doc.company):
        return None

    if not erpnext.__version__.startswith("16"):
        item_wise_tax_detail = frappe.db.get_value(
            "Sales Taxes and Charges",
            {"parent": doc.name},
            "item_wise_tax_detail",
        )
        item_taxes = json.loads(item_wise_tax_detail or "{}")

        item_tax_percent = (
            item_row.tax_rate
            if item_row.tax_rate is not None
            else item_taxes.get(item_row.item_code, [0, 0])[0]
        )

        item_tax_total = (
            item_row.tax_amount
            if item_row.tax_amount is not None
            else item_taxes.get(item_row.item_code, [0, 0])[1]
        ) / doc.conversion_rate

    else:
        item_tax_percent = item_row.tax_rate
        item_tax_total = item_row.tax_amount / doc.conversion_rate

    item_total_after_tax = item_tax_total + item_row.net_amount
    return frappe._dict(
        {
            "item_tax_percent": item_tax_percent,
            "item_tax_total": item_tax_total,
            "item_total_after_tax": item_total_after_tax,
        }
    )


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
    details_dict = {"xml_data": None}

    # Replaced DB lookups to strictly enforce printing from XML source mapping
    siaf = frappe.get_last_doc(
        "Sales Invoice Additional Fields",
        {"sales_invoice": getattr(sales_invoice, "name", sales_invoice)},
    )
    if siaf:
        xml_string = siaf.get_signed_xml()
        if xml_string:
            details_dict["xml_data"] = parse_xml_to_dict(xml_string)
            qr_base64_tlv = details_dict["xml_data"]["invoice"].get("qr_code")
            if qr_base64_tlv:
                qr_png = generate_qrcode(qr_base64_tlv)
                if qr_png:
                    details_dict["xml_data"]["invoice"]["qr_image_src"] = (
                        "data:image/png;base64," + qr_png
                    )
    return details_dict


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
