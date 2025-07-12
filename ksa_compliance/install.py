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
				module=ksa_compliance_module,
				read_only = True,
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
			)
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
		]
	}
	create_custom_fields(custom_fields)
