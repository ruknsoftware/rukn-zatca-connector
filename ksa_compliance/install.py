import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

ksa_compliance_module = "KSA Compliance"


def after_install():
    add_custom_fields()
    add_property_setters()


def add_custom_fields():
    custom_fields = {
        "Payment Entry": [
            dict(
                fieldname="posting_time",
                label="Posting Time",
                fieldtype="Time",
                insert_after="posting_date",
                mandatory_depends_on="eval:doc.is_advance_payment ||  doc.is_advance_payment_depends_on_entry",
                module=ksa_compliance_module,
            ),
            dict(
                fieldname="is_advance_payment",
                label="IS Advance Payment",
                fieldtype="Check",
                insert_after="payment_type",
                module=ksa_compliance_module,
                read_only=True,
            ),
            dict(
                fieldname="is_advance_payment_depends_on_entry",
                label="IS Advance Payment Depends On Entry",
                fieldtype="Check",
                insert_after="is_advance_payment",
                module=ksa_compliance_module,
            ),
            dict(
                fieldname="advance_payment_entry_taxes_and_charges",
                label="Advance Payment Entry Sales Taxes and Charges",
                fieldtype="Link",
                options="Sales Taxes and Charges Template",
                insert_after="is_advance_payment_depends_on_entry",
                read_only_depends_on="eval:!doc.is_advance_payment_depends_on_entry",
                mandatory_depends_on="eval:doc.is_advance_payment_depends_on_entry",
                module=ksa_compliance_module,
            ),
            dict(
                fieldname="invoice_doctype",
                label="Invoice Doctype",
                fieldtype="Select",
                options="Sales Invoice",
                insert_after="mode_of_payment",
                module=ksa_compliance_module,
                hidden=True,
                read_only=True,
            ),
            dict(
                fieldname="advance_payment_invoice",
                label="Advance Payment Invoice",
                fieldtype="Dynamic Link",
                options="invoice_doctype",
                insert_after="invoice_doctype",
                module=ksa_compliance_module,
                read_only=True,
            ),
            dict(
                fieldname="allocated_tax",
                label="Allocated Tax",
                fieldtype="Currency",
                options="Company:company:default_currency",
                insert_after="base_total_allocated_amount",
                module=ksa_compliance_module,
                read_only=True,
            ),
            dict(
                fieldname="unallocated_tax",
                label="Unallocated Tax",
                fieldtype="Currency",
                options="Company:company:default_currency",
                insert_after="unallocated_amount",
                module=ksa_compliance_module,
                read_only=True,
            ),
        ],
        "Sales Invoice": [
            dict(
                fieldname="advance_payment",
                label="Advance Payment",
                fieldtype="Section Break",
                insert_after="amended_from",
                module=ksa_compliance_module,
                collapsible=1,
            ),
            dict(
                fieldname="mode_of_payment",
                label="Mode Of Payment",
                fieldtype="Link",
                insert_after="advance_payment",
                options="Mode of Payment",
                module=ksa_compliance_module,
                read_only=True,
            ),
            dict(
                fieldname="mode_of_payment_account",
                label="Mode Of Payment Account",
                fieldtype="Link",
                insert_after="mode_of_payment",
                options="Account",
                module=ksa_compliance_module,
                read_only=True,
            ),
            dict(
                fieldname="advance_payment_clm_brk",
                label="",
                fieldtype="Column Break",
                insert_after="mode_of_payment_account",
                module=ksa_compliance_module,
                print_hide=1,
            ),
            dict(
                fieldname="reference_no",
                label="Cheque/Reference No",
                fieldtype="Data",
                insert_after="advance_payment_clm_brk",
                module=ksa_compliance_module,
                print_hide=1,
                read_only=True,
            ),
            dict(
                fieldname="reference_date",
                label="Cheque/Reference Date",
                fieldtype="Date",
                insert_after="reference_no",
                module=ksa_compliance_module,
                read_only=True,
            ),
            dict(
                fieldname="advance_payment_invoices",
                label="Advance Payment Invoices",
                fieldtype="Table",
                insert_after="advances",
                options="Sales Invoice Advance Payment",
                module=ksa_compliance_module,
                read_only=True,
            ),
        ],
        "Mode of Payment": [
            dict(
                fieldname="custom_zatca_payment_means_code",
                label="ZATCA Payment Means Code",
                fieldtype="Data",
                insert_after="accounts",
                dt="Mode of Payment",
                reqd=0,
                description="Value from <a href='https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred4461.htm' target='_blank'>UN/EDIFACT 4461</a>",
                module=ksa_compliance_module,
            )
        ],
        "Journal Entry": [
            dict(
                fieldname="advance_payment_entry",
                label="Advance Payment Entry",
                fieldtype="Link",
                options="Payment Entry",
                insert_after="voucher_type",
                read_only=True,
                module=ksa_compliance_module,
            )
        ],
    }
    create_custom_fields(custom_fields)


def add_property_setters():

    setter_name = "Mode of Payment-field_order"

    if not frappe.db.exists("Property Setter", setter_name):
        ps_doc = make_property_setter(
            doctype="Mode of Payment",
            fieldname=None,
            property="field_order",
            value='["mode_of_payment", "enabled", "type", "accounts", "custom_zatca_payment_means_code"]',
            property_type="Data",
            for_doctype=True,
        )

        ps_doc.module = ksa_compliance_module
        ps_doc.save(ignore_permissions=True)
