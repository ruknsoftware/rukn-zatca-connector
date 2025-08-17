import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc
from erpnext.controllers.sales_and_purchase_return import make_return_doc as erpnext_make_return_doc
from erpnext.controllers.sales_and_purchase_return import get_returned_qty_map_for_row
from ksa_compliance.utils.advance_payment_invoice import invoice_has_advance_item
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings


@frappe.whitelist()
def make_sales_return(source_name, target_doc=None):
    sales_invoice = frappe.get_doc("Sales Invoice", source_name)
    settings = ZATCABusinessSettings.for_company(sales_invoice.company)
    if not invoice_has_advance_item(sales_invoice, settings):
        return erpnext_make_return_doc("Sales Invoice", source_name, target_doc)

    return make_return_doc("Sales Invoice", source_name, target_doc)


def make_return_doc(doctype: str, source_name: str, target_doc=None, return_against_rejected_qty=False):
    company = frappe.db.get_value(doctype, source_name, "company")
    default_warehouse_for_sales_return = frappe.get_cached_value(
        "Company", company, "default_warehouse_for_sales_return"
    )

    if doctype == "Sales Invoice":
        inv_is_consolidated, inv_is_pos = frappe.db.get_value(
            "Sales Invoice", source_name, ["is_consolidated", "is_pos"]
        )
        if inv_is_consolidated and inv_is_pos:
            frappe.throw(
                _("Cannot create return for consolidated invoice {0}.").format(source_name),
                title=_("Cannot Create Return"),
            )

    def set_missing_values(source, target):
        doc = frappe.get_doc(target)
        doc.is_return = 1
        doc.ignore_pricing_rule = 1
        doc.pricing_rules = []
        doc.return_against = source.name
        doc.set_warehouse = ""
        if doctype == "Sales Invoice" or doctype == "POS Invoice":
            doc.is_pos = source.is_pos

            # look for Print Heading "Credit Note"
            if not doc.select_print_heading:
                doc.select_print_heading = frappe.get_cached_value("Print Heading", _("Credit Note"))

        elif doctype == "Purchase Invoice":
            # look for Print Heading "Debit Note"
            doc.select_print_heading = frappe.get_cached_value("Print Heading", _("Debit Note"))
            if source.tax_withholding_category:
                doc.set_onload("supplier_tds", source.tax_withholding_category)
        elif doctype == "Delivery Note":
            # manual additions to the return should hit the return warehous, too
            doc.set_warehouse = default_warehouse_for_sales_return

        for tax in doc.get("taxes") or []:
            if tax.charge_type == "Actual":
                tax.tax_amount = -1 * tax.tax_amount

        if doc.get("is_return"):
            if doc.doctype == "Sales Invoice" or doc.doctype == "POS Invoice":
                doc.consolidated_invoice = ""
                # no copy enabled for party_account_currency
                doc.party_account_currency = source.party_account_currency
                doc.set("payments", [])
                doc.update_billed_amount_in_delivery_note = True
                for data in source.payments:
                    paid_amount = 0.00
                    base_paid_amount = 0.00
                    data.base_amount = flt(
                        data.amount * source.conversion_rate, source.precision("base_paid_amount")
                    )
                    paid_amount += data.amount
                    base_paid_amount += data.base_amount
                    doc.append(
                        "payments",
                        {
                            "mode_of_payment": data.mode_of_payment,
                            "type": data.type,
                            "amount": -1 * paid_amount,
                            "base_amount": -1 * base_paid_amount,
                            "account": data.account,
                            "default": data.default,
                        },
                    )
                if doc.is_pos:
                    doc.paid_amount = -1 * source.paid_amount
            elif doc.doctype == "Purchase Invoice":
                doc.paid_amount = -1 * source.paid_amount
                doc.base_paid_amount = -1 * source.base_paid_amount
                doc.payment_terms_template = ""
                doc.payment_schedule = []

        if doc.get("is_return") and hasattr(doc, "packed_items"):
            for d in doc.get("packed_items"):
                d.qty = d.qty * -1

        if doc.get("discount_amount"):
            doc.discount_amount = -1 * source.discount_amount

        if doctype == "Subcontracting Receipt":
            doc.set_warehouse = source.set_warehouse
            doc.supplier_warehouse = source.supplier_warehouse
        else:
            doc.run_method("calculate_taxes_and_totals")

    def update_item(source_doc, target_doc, source_parent):
        target_doc.qty = -1 * source_doc.qty
        target_doc.pricing_rules = None
        if doctype in ["Purchase Receipt", "Subcontracting Receipt"]:
            returned_qty_map = get_returned_qty_map_for_row(
                source_parent.name, source_parent.supplier, source_doc.name, doctype
            )

            if doctype == "Subcontracting Receipt":
                target_doc.received_qty = -1 * flt(source_doc.qty)
            else:
                target_doc.received_qty = -1 * flt(
                    source_doc.received_qty - (returned_qty_map.get("received_qty") or 0)
                )
                target_doc.rejected_qty = -1 * flt(
                    source_doc.rejected_qty - (returned_qty_map.get("rejected_qty") or 0)
                )

            target_doc.qty = -1 * flt(source_doc.qty - (returned_qty_map.get("qty") or 0))

            if hasattr(target_doc, "stock_qty") and not return_against_rejected_qty:
                target_doc.stock_qty = -1 * flt(
                    source_doc.stock_qty - (returned_qty_map.get("stock_qty") or 0)
                )
                target_doc.received_stock_qty = -1 * flt(
                    source_doc.received_stock_qty - (returned_qty_map.get("received_stock_qty") or 0)
                )

            if doctype == "Subcontracting Receipt":
                target_doc.subcontracting_order = source_doc.subcontracting_order
                target_doc.subcontracting_order_item = source_doc.subcontracting_order_item
                target_doc.rejected_warehouse = source_doc.rejected_warehouse
                target_doc.subcontracting_receipt_item = source_doc.name
            else:
                target_doc.purchase_order = source_doc.purchase_order
                target_doc.purchase_order_item = source_doc.purchase_order_item
                target_doc.rejected_warehouse = source_doc.rejected_warehouse
                target_doc.purchase_receipt_item = source_doc.name

            if doctype == "Purchase Receipt" and return_against_rejected_qty:
                target_doc.qty = -1 * flt(source_doc.rejected_qty - (returned_qty_map.get("qty") or 0))
                target_doc.rejected_qty = 0.0
                target_doc.rejected_warehouse = ""
                target_doc.warehouse = source_doc.rejected_warehouse
                target_doc.received_qty = target_doc.qty
                target_doc.return_qty_from_rejected_warehouse = 1

        elif doctype == "Purchase Invoice":
            returned_qty_map = get_returned_qty_map_for_row(
                source_parent.name, source_parent.supplier, source_doc.name, doctype
            )
            target_doc.received_qty = -1 * flt(
                source_doc.received_qty - (returned_qty_map.get("received_qty") or 0)
            )
            target_doc.rejected_qty = -1 * flt(
                source_doc.rejected_qty - (returned_qty_map.get("rejected_qty") or 0)
            )
            target_doc.qty = -1 * flt(source_doc.qty - (returned_qty_map.get("qty") or 0))

            target_doc.stock_qty = -1 * flt(source_doc.stock_qty - (returned_qty_map.get("stock_qty") or 0))
            target_doc.purchase_order = source_doc.purchase_order
            target_doc.purchase_receipt = source_doc.purchase_receipt
            target_doc.rejected_warehouse = source_doc.rejected_warehouse
            target_doc.po_detail = source_doc.po_detail
            target_doc.pr_detail = source_doc.pr_detail
            target_doc.purchase_invoice_item = source_doc.name

        elif doctype == "Delivery Note":
            returned_qty_map = get_returned_qty_map_for_row(
                source_parent.name, source_parent.customer, source_doc.name, doctype
            )
            target_doc.qty = -1 * flt(source_doc.qty - (returned_qty_map.get("qty") or 0))
            target_doc.stock_qty = -1 * flt(source_doc.stock_qty - (returned_qty_map.get("stock_qty") or 0))

            target_doc.against_sales_order = source_doc.against_sales_order
            target_doc.against_sales_invoice = source_doc.against_sales_invoice
            target_doc.so_detail = source_doc.so_detail
            target_doc.si_detail = source_doc.si_detail
            target_doc.expense_account = source_doc.expense_account
            target_doc.dn_detail = source_doc.name
            if default_warehouse_for_sales_return:
                target_doc.warehouse = default_warehouse_for_sales_return
        elif doctype == "Sales Invoice" or doctype == "POS Invoice":

            # OUR UPDATE
            # CALCULATE ITEM ADVANCE RATE DEPENDING ON OUTSTANDING AMOUNT
            target_doc.rate = round(source_parent.outstanding_amount - (
                    (source_parent.outstanding_amount * source_doc.tax_rate) / source_parent.grand_total), 2)
            # END OF UPDATE

            returned_qty_map = get_returned_qty_map_for_row(
                source_parent.name, source_parent.customer, source_doc.name, doctype
            )
            target_doc.qty = -1 * flt(source_doc.qty - (returned_qty_map.get("qty") or 0))
            target_doc.stock_qty = -1 * flt(source_doc.stock_qty - (returned_qty_map.get("stock_qty") or 0))

            target_doc.sales_order = source_doc.sales_order
            target_doc.delivery_note = source_doc.delivery_note
            target_doc.so_detail = source_doc.so_detail
            target_doc.dn_detail = source_doc.dn_detail
            target_doc.expense_account = source_doc.expense_account

            if doctype == "Sales Invoice":
                target_doc.sales_invoice_item = source_doc.name
            else:
                target_doc.pos_invoice_item = source_doc.name

            if default_warehouse_for_sales_return:
                target_doc.warehouse = default_warehouse_for_sales_return

        # OUR UPDATE
        # CHECK IF use_serial_batch_fields AND serial_and_batch_bundle IS ON Sales Invoice Item ON ERPNEXT VERSION
        use_serial_batch_fields = getattr(source_doc, "use_serial_batch_fields", 0)
        serial_and_batch_bundle = getattr(source_doc, "serial_and_batch_bundle", 0)
        if not use_serial_batch_fields and serial_and_batch_bundle:
            target_doc.serial_no = None
            target_doc.batch_no = None

        if (
                (source_doc.serial_no or source_doc.batch_no)
                and not serial_and_batch_bundle
                and not use_serial_batch_fields
        ):
            target_doc.set("use_serial_batch_fields", 1)

        if source_doc.item_code and target_doc.get("use_serial_batch_fields"):
            item_details = frappe.get_cached_value(
                "Item", source_doc.item_code, ["has_batch_no", "has_serial_no"], as_dict=1
            )

            if not item_details.has_batch_no and not item_details.has_serial_no:
                return

            update_non_bundled_serial_nos(source_doc, target_doc, source_parent)

    def update_non_bundled_serial_nos(source_doc, target_doc, source_parent):
        from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

        if source_doc.serial_no:
            returned_serial_nos = get_returned_non_bundled_serial_nos(source_doc, source_parent)
            serial_nos = list(set(get_serial_nos(source_doc.serial_no)) - set(returned_serial_nos))
            if serial_nos:
                target_doc.serial_no = "\n".join(serial_nos)

        if source_doc.get("rejected_serial_no"):
            returned_serial_nos = get_returned_non_bundled_serial_nos(
                source_doc, source_parent, serial_no_field="rejected_serial_no"
            )
            rejected_serial_nos = list(
                set(get_serial_nos(source_doc.rejected_serial_no)) - set(returned_serial_nos)
            )
            if rejected_serial_nos:
                target_doc.rejected_serial_no = "\n".join(rejected_serial_nos)

    def get_returned_non_bundled_serial_nos(child_doc, parent_doc, serial_no_field="serial_no"):
        from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

        return_ref_field = frappe.scrub(child_doc.doctype)
        if child_doc.doctype == "Delivery Note Item":
            return_ref_field = "dn_detail"

        serial_nos = []

        fields = [f"`{'tab' + child_doc.doctype}`.`{serial_no_field}`"]

        filters = [
            [parent_doc.doctype, "return_against", "=", parent_doc.name],
            [parent_doc.doctype, "is_return", "=", 1],
            [child_doc.doctype, return_ref_field, "=", child_doc.name],
            [parent_doc.doctype, "docstatus", "=", 1],
        ]

        for row in frappe.get_all(parent_doc.doctype, fields=fields, filters=filters):
            serial_nos.extend(get_serial_nos(row.get(serial_no_field)))

        return serial_nos

    def update_terms(source_doc, target_doc, source_parent):
        target_doc.payment_amount = -source_doc.payment_amount

    def item_condition(doc):
        if return_against_rejected_qty:
            return doc.rejected_qty

        return doc.qty

    doclist = get_mapped_doc(
        doctype,
        source_name,
        {
            doctype: {
                "doctype": doctype,
                "validation": {
                    "docstatus": ["=", 1],
                },
            },
            doctype + " Item": {
                "doctype": doctype + " Item",
                "field_map": {"serial_no": "serial_no", "batch_no": "batch_no", "bom": "bom"},
                "postprocess": update_item,
                "condition": item_condition,
            },
            "Payment Schedule": {"doctype": "Payment Schedule", "postprocess": update_terms},
        },
        target_doc,
        set_missing_values,
    )

    return doclist

