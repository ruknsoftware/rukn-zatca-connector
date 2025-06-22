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
			),
			dict(
				fieldname="zatca_advance_payment_column_break1",
				fieldtype="Column Break",
				insert_after="paid_amount",
				module=ksa_compliance_module
			),
			dict(
				fieldname="net_total",
				label="Advance Payment Total",
				fieldtype="Currency",
				insert_after="zatca_advance_payment_column_break1",
				depends_on="eval:doc.is_advance_payment == 1",
				read_only=1,
				module=ksa_compliance_module
			),
			dict(
				fieldname="tax_amount",
				label="Advance Payment Tax Amount",
				fieldtype="Currency",
				insert_after="net_total",
				depends_on="eval:doc.is_advance_payment == 1",
				read_only=1,
				module=ksa_compliance_module
			),

		],
	}
	create_custom_fields(custom_fields)
