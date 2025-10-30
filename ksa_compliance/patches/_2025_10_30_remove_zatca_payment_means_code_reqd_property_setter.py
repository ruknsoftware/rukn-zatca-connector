import frappe


def execute():
    """Remove the property setter that made custom_zatca_payment_means_code required in Mode of Payment"""
    doctype = "Mode of Payment"
    fieldname = "custom_zatca_payment_means_code"
    setter_name = f"{doctype}-{fieldname}-reqd"

    if frappe.db.exists("Property Setter", setter_name):
        frappe.delete_doc("Property Setter", setter_name, ignore_permissions=True, force=True)
        frappe.db.commit()
