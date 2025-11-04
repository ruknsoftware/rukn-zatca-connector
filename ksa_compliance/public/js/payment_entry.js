frappe.ui.form.on('Payment Entry', {
    onload: function(frm) {
        if (!frm.doc.posting_time && frm.is_new()) {
            frm.set_value("posting_time", frappe.datetime.now_time());
        }
    },
    refresh: function (frm){
        frm.trigger("remove_un_reconcile_button");
        if (frm.doc.is_advance_payment_depends_on_entry && frm.doc.docstatus === 1 && frm.doc.unallocated_amount !== 0){
            frm.add_custom_button(
                __("Return Advance Payment"),
                () => {
                    let d = new frappe.ui.Dialog({
                        title: __("Return Advance Payment"),
                        fields: [
                            {
                                label: __("Amount to Return"),
                                fieldname: "amount",
                                fieldtype: "Float",
                                reqd: 1,
                                description: __("Unallocated Amount: " + frm.doc.unallocated_amount),
                            }
                        ],
                        primary_action_label: __("Create Return Payment"),
                        primary_action(values) {
                            if (values.amount > frm.doc.unallocated_amount) {
                                frappe.msgprint({
                                    title: __("Invalid Amount"),
                                    message: __("Amount cannot exceed Unallocated Amount."),
                                    indicator: "red",
                                });
                                return;
                            }
                            frappe.call({
                                method: "ksa_compliance.standard_doctypes.payment_entry.return_advance_payment_entry_doc",
                                args: {
                                    payment_entry_name: frm.doc.name,
                                    return_amount: values.amount,
                                },
                                callback: function(r) {
                                    if (!r.exc) {
                                        let doc_link = frappe.utils.get_form_link(
                                            "Journal Entry",
                                            r.message,
                                            true
                                        );
                                        frappe.msgprint({
                                            title: __("Return Processed Successfully"),
                                            message: __(
                                                "A Journal Entry {0} has been created to record the returned advance payment of {1}.",
                                                [doc_link,format_currency(values.amount, frm.doc.company_currency)]
                                            ),
                                            indicator: "green",
                                        });
                                        frm.reload_doc();
                                    }
                                },
                            });

                            d.hide();
                        },
                    });
                    d.show();
                },
                __("Actions")
            );
        }
    },
    remove_un_reconcile_button: function (frm){
        if (frm.doc.is_advance_payment === 1 & frm.doc.payment_type === "Receive" & frm.doc.party_type === "Customer"){
            frm.remove_custom_button(__("UnReconcile"), __("Actions"));
        }
    },
    party_type: function (frm){
        if (frm.doc.party_type !== "Customer"){
            frm.set_value("is_advance_payment_depends_on_entry", false);
        }
    }
});
