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
        }
    })

    frappe.ui.form.on('Sales Invoice Item', {
        items_add(frm)    { update_sales_invoice_mode_of_payment(frm); },
        items_remove(frm) { update_sales_invoice_mode_of_payment(frm); },
        item_code(frm)    { update_sales_invoice_mode_of_payment(frm); }
    })
})
