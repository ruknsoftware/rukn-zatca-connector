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
                fieldname="is_advance_payment",
                label="IS Advance Payment",
                fieldtype="Check",
                insert_after="payment_type",
                module=ksa_compliance_module,
                read_only=True,
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
        ],
        "Sales Invoice": [
            dict(
                fieldname="mode_of_payment",
                label="Mode Of Payment",
                fieldtype="Link",
                insert_after="company_tax_id",
                options="Mode of Payment",
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


def after_migrate():

    doctype = "Mode of Payment"
    fieldname = "custom_zatca_payment_means_code"
    setter_name = f"{doctype}-{fieldname}-reqd"

    if not frappe.db.exists("Property Setter", setter_name):
        ps_doc = make_property_setter(
            doctype=doctype,
            fieldname=fieldname,
            property="reqd",
            value="1",
            property_type="Check",
            for_doctype=False,
        )

        ps_doc.module = ksa_compliance_module
        ps_doc.save(ignore_permissions=True)
