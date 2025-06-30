frappe.require("/assets/ksa_compliance/js/update_invoice_mode_of_payment.js").then(() => {

    frappe.ui.form.on('POS Invoice', {
        refresh:function (frm){
            update_sales_invoice_mode_of_payment(frm);
        }
    })

    frappe.ui.form.on('POS Invoice Item', {
        items_add(frm)    { update_sales_invoice_mode_of_payment(frm); },
        items_remove(frm) { update_sales_invoice_mode_of_payment(frm); },
        item_code(frm)    { update_sales_invoice_mode_of_payment(frm); }
    })
})