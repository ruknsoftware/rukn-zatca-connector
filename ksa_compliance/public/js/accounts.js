erpnext.accounts.pos = {
	setup: function(doctype) {
		frappe.ui.form.on(doctype, {
			mode_of_payment: function(frm, cdt, cdn) {
				var d = locals[cdt][cdn];
				erpnext.accounts.pos.get_payment_mode_account(frm, d.mode_of_payment, function(account){
					frappe.model.set_value(cdt, cdn, 'account', account)
				})
			}
		});
	},

	get_payment_mode_account: function(frm, mode_of_payment, callback) {
		if(!frm.doc.company) {
			frappe.throw({message:__("Please select a Company first."), title: __("Mandatory")});
		}

		if(!mode_of_payment) {
			return;
		}

		return  frappe.call({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
			args: {
				"mode_of_payment": mode_of_payment,
				"company": frm.doc.company
			},
			callback: function(r, rt) {
				if(r.message) {
					callback(r.message.account)
				}
			}
		});
	}
}
