from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	add_custom_fields()


def add_custom_fields():
	ksa_compliance_module = "KSA Compliance"
	custom_fields = {
		"Payment Entry": [
			dict(
				fieldname="is_advance_payment",
				label="IS Advance Payment",
				fieldtype="Check",
				insert_after="payment_type",
				module=ksa_compliance_module
			)
		],
	}
	create_custom_fields(custom_fields)
