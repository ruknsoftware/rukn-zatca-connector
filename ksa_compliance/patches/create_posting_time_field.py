import frappe

from ksa_compliance.install import after_install


def execute():

    after_install()
    frappe.db.sql(
        """
            UPDATE `tabPayment Entry`
            SET posting_time = TIME(creation)
            WHERE (is_advance_payment = 1 OR is_advance_payment_depends_on_entry = 1)
        """
    )
