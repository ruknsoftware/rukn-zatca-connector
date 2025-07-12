frappe.ui.form.on('Payment Entry', {
    refresh: function (frm){
        frm.trigger("remove_un_reconcile_button");

    },
    remove_un_reconcile_button: function (frm){
        if (frm.doc.is_advance_payment === 1 & frm.doc.payment_type === "Receive" & frm.doc.party_type === "Customer"){
            frm.remove_custom_button(__("UnReconcile"), __("Actions"));
        }
    }
});
