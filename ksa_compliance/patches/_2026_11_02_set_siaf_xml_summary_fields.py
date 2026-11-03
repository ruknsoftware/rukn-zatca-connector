import frappe

from ksa_compliance import logger
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    get_xml_summary_values,
)
from ksa_compliance.utils.xml_parser import parse_xml_to_dict

DOCTYPE = "Sales Invoice Additional Fields"
# The XML is a large Long Text field, so read it in batches instead of loading every record at once
BATCH_SIZE = 500


def execute():
    """Fill issue date/time, currency, tax totals and invoice type on existing SIAFs from their stored XML"""
    updated = 0
    skipped = 0
    last_name = ""
    while True:
        # Keyset pagination: records we skip keep an empty issue_date, so an offset over the same filter would loop
        rows = frappe.get_all(
            DOCTYPE,
            filters={"issue_date": ["is", "not set"], "name": [">", last_name]},
            fields=["name", "invoice_xml", "tax_currency", "invoice_type_code"],
            order_by="name asc",
            limit_page_length=BATCH_SIZE,
        )
        if not rows:
            break

        for row in rows:
            if _backfill(row):
                updated += 1
            else:
                skipped += 1

        last_name = rows[-1].name
        frappe.db.commit()

    message = f"SIAF summary fields backfill: {updated} updated, {skipped} skipped"
    logger.info(message)
    print(message)


def _backfill(row: frappe._dict) -> bool:
    xml = row.invoice_xml
    if not xml:
        # SIAFs created before the XML field existed keep their XML as an attachment
        try:
            xml = frappe.get_doc(DOCTYPE, row.name).get_signed_xml()
        except Exception:
            # e.g. the attachment's file is missing on disk; don't let one record fail the migration
            logger.exception(f"Skipping {row.name}: could not read XML attachment")
            return False
    if not xml:
        logger.warning(f"Skipping {row.name}: no XML")
        return False

    try:
        values = get_xml_summary_values(parse_xml_to_dict(xml)["invoice"])
    except Exception:
        logger.exception(f"Skipping {row.name}: could not parse XML")
        return False

    if not values.issue_date:
        logger.warning(f"Skipping {row.name}: XML has no issue date")
        return False
    if not values.invoice_type_code_label:
        logger.warning(
            f"Skipping {row.name}: unknown invoice type code '{values.invoice_type_code}'"
        )
        return False

    # Keep values already stored on the record
    if row.tax_currency:
        values.pop("tax_currency")
    if row.invoice_type_code:
        values.pop("invoice_type_code")

    # SIAF is submittable, and nearly all records are submitted: write directly instead of doc.save()
    frappe.db.set_value(DOCTYPE, row.name, values, update_modified=False)
    return True
