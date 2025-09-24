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
            if (frm.doc.is_return){
                is_advance_invoice(frm).then(is_advance => {
                    frm.set_df_property("update_outstanding_for_self", "read_only", is_advance ? 1 : 0);
                    frm.set_value("update_outstanding_for_self", 1);
                    frm.refresh_field("update_outstanding_for_self");
                });
            }
        },

        customer: function(frm) {
            frm.trigger("apply_advance_payments");
        },
        mode_of_payment: function(frm){
            frm.trigger("fetch_mode_of_payment_account");
        },
        mode_of_payment_account: function (frm){
            frm.trigger("setup_reference_no_and_date_properties");
        },
        fetch_mode_of_payment_account: function (frm){
            frappe.call({
                method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
                args: {
                    mode_of_payment: frm.doc.mode_of_payment,
					company: frm.doc.company,
                },
                callback: function(r) {
                    if(r.message) {
                        frm.set_value("mode_of_payment_account", r.message.account);
                    }
                }
            });
            frm.set_df_property("mode_of_payment_account", "read_only", 0);
            frm.refresh_field("mode_of_payment_account");
            frm.set_query('mode_of_payment_account', function (doc){
                return {
                    filters: [
                        ["Account", "account_type", "in", "Bank, Cash, Receivable"],
                        ["Account", "is_group", "=", 0],
                        ["Account", "company", "=", frm.doc.company],
                    ],
                };
            });
        },
        setup_reference_no_and_date_properties: function (frm, mode_of_payment_account){
            frappe.call({
                method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_account_details",
                args: {
                    account:frm.doc.mode_of_payment_account,
                    date:frm.doc.posting_date,
                    cost_center:frm.doc.cost_center,
                },
                callback: function(response) {
                    const type = response.message.account_type;
                    if (type === "Bank"){
                        frm.set_df_property("reference_no", "read_only", 0);
                        frm.toggle_reqd("reference_no", 1);
                        frm.set_df_property("reference_date", "read_only", 0);
                        frm.toggle_reqd("reference_date", 1);
                    }else {
                        frm.set_df_property("reference_no", "read_only", 1);
                        frm.toggle_reqd("reference_no", 0);
                        frm.set_df_property("reference_date", "read_only", 1);
                        frm.toggle_reqd("reference_date", 0);
                    }
                    frm.refresh_field("reference_no");
                    frm.refresh_field("reference_date");
                }
            });
        },
        apply_advance_payments: function (frm){
            if (frm.doc.customer) {
                frappe.call({
                    method: "ksa_compliance.standard_doctypes.sales_invoice_advance.get_invoice_applicable_advance_payments",
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
        },
    })

    frappe.ui.form.on('Sales Invoice Item', {
        items_add(frm)    { update_sales_invoice_mode_of_payment(frm); },
        items_remove(frm) { update_sales_invoice_mode_of_payment(frm); },
        item_code(frm)    { update_sales_invoice_mode_of_payment(frm); }
    })
})
