frappe.require("/assets/ksa_compliance/js/update_invoice_mode_of_payment.js").then(() => {
    frappe.ui.form.on('Sales Invoice', {
        setup: function (frm) {
            frm.set_query('custom_return_against_additional_references', function (doc) {
                // Similar to logic in erpnext/public/js/controllers/transaction.js for return_against
                let filters = {
                    'docstatus': 1,
                    'is_return': 0,
                    'company': doc.company
                };
                if (frm.fields_dict['customer'] && doc.customer) filters['customer'] = doc.customer;
                if (frm.fields_dict['supplier'] && doc.supplier) filters['supplier'] = doc.supplier;

                return {
                    filters: filters
                };
            });
        },
        refresh:function (frm){
            update_sales_invoice_mode_of_payment(frm);
        },
        customer: function(frm) {
            if (frm.doc.customer) {
                frappe.db.get_value(
                    "ZATCA Business Settings",
                    { company: frm.doc.company },
                    "auto_apply_advance_payments"
                ).then(response => {
                    if (response.message.auto_apply_advance_payments === 1) {
                        frappe.call({
                            method: "ksa_compliance.standard_doctypes.sales_invoice_advance.get_customer_advance_payments",
                            args: {self: frm.doc,},
                            callback: function (response) {
                                frm.clear_table("advances");
                                (response.message || []).forEach(advance => {
                                    let advance_row = frappe.model.add_child(frm.doc, "Sales Invoice Advance", "advances");
                                    advance_row.doctype = advance.doctype
                                    advance_row.reference_type = advance.reference_type
                                    advance_row.reference_name = advance.reference_name
                                    advance_row.reference_row = advance.reference_row
                                    advance_row.remarks = advance.remarks
                                    advance_row.advance_amount = advance.advance_amount
                                    advance_row.allocated_amount = advance.allocated_amount
                                    advance_row.ref_exchange_rate = advance.ref_exchange_rate
                                });
                                frm.refresh_field("advances");
                            }
                        });
                    }
                })
            }
        },
    })

    frappe.ui.form.on('Sales Invoice Item', {
        items_add(frm)    { update_sales_invoice_mode_of_payment(frm); },
        items_remove(frm) { update_sales_invoice_mode_of_payment(frm); },
        item_code(frm)    { update_sales_invoice_mode_of_payment(frm); }
    })
})
