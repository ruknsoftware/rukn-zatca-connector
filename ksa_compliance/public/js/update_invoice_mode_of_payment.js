function is_advance_invoice(frm) {
    return frappe.db.get_value(
        "ZATCA Business Settings",
        { company: frm.doc.company },
        "advance_payment_item"
    ).then(response => {
        const advance_item = response.message.advance_payment_item;
        return (frm.doc.items || []).some(row => row.item_code === advance_item);
    });
}

function update_sales_invoice_mode_of_payment(frm) {
    is_advance_invoice(frm).then(is_advance => {
        frm.set_df_property("mode_of_payment", "read_only", is_advance ? 0 : 1);
        frm.toggle_reqd("mode_of_payment", is_advance);
        frm.refresh_field("mode_of_payment");
    });
}