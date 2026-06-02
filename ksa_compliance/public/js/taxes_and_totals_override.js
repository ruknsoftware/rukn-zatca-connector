frappe.provide("erpnext.taxes_and_totals");

const erpnext_major = parseInt((frappe.boot.versions.erpnext).split(".")[0]);
if (erpnext.taxes_and_totals && erpnext_major < 16) {
    erpnext.taxes_and_totals.prototype.get_current_tax_amount = function (item, tax, item_tax_map) {
		var tax_rate = this._get_tax_rate(tax, item_tax_map);
		var current_tax_amount = 0.0;
		var current_net_amount = 0.0;
		// To set row_id by default as previous row.
		if(["On Previous Row Amount", "On Previous Row Total"].includes(tax.charge_type)) {
			if (tax.idx === 1) {
				frappe.throw(
					__("Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"));
			}
			if (!tax.row_id) {
				tax.row_id = tax.idx - 1;
			}
		}
		if(tax.charge_type == "Actual") {
			current_net_amount = item.net_amount
			// distribute the tax amount proportionally to each item row
			var actual = flt(tax.tax_amount, precision("tax_amount", tax));
			current_tax_amount = this.frm.doc.net_total ?
				((item.net_amount / this.frm.doc.net_total) * actual) : 0.0;

		} else if(tax.charge_type == "On Net Total") {
			if (tax.account_head in item_tax_map) {
				current_net_amount = item.net_amount
			};
			if (tax.included_in_print_rate){
				var net_amount = item.amount / (1 + tax_rate / 100.0)
				current_tax_amount = item.amount - net_amount
			}else {
				current_tax_amount = (tax_rate / 100.0) * item.net_amount;
			}
		} else if(tax.charge_type == "On Previous Row Amount") {
			current_net_amount = this.frm.doc["taxes"][cint(tax.row_id) - 1].tax_amount_for_current_item
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.doc["taxes"][cint(tax.row_id) - 1].tax_amount_for_current_item;

		} else if(tax.charge_type == "On Previous Row Total") {
			current_net_amount = this.frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_for_current_item
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_for_current_item;
		} else if (tax.charge_type == "On Item Quantity") {
			current_tax_amount = tax_rate * item.qty;
		}

		if (!tax.dont_recompute_tax) {
			this.set_item_wise_tax(item, tax, tax_rate, current_tax_amount);
		}
		// return [current_net_amount, flt(current_tax_amount, precision("tax_amount", tax))];
		const erpnext_version = frappe.boot?.versions?.erpnext;
		// Ensure that the version checked is formatted as semantic version strings
		if (is_version_greater_or_equal(erpnext_version, "15.101")){
			return [current_net_amount, flt(current_tax_amount, precision("tax_amount", tax))];

		}else {
			return flt(current_tax_amount, precision("tax_amount", tax))
		}

	};


    erpnext.taxes_and_totals.prototype.set_item_wise_tax = function (item, tax, tax_rate, current_tax_amount) {
        // store tax breakup for each item
		let tax_detail = tax.item_wise_tax_detail;
		let key = item.item_code || item.item_name;

		if (typeof tax_detail == "string") {
			tax.item_wise_tax_detail = JSON.parse(tax.item_wise_tax_detail);
			tax_detail = tax.item_wise_tax_detail;
		} else if (!tax_detail || typeof tax_detail !== "object") {
			tax.item_wise_tax_detail = {};
			tax_detail = tax.item_wise_tax_detail;
		}

		let _item_wise_tax_amount = current_tax_amount * this.frm.doc.conversion_rate;
		let item_wise_tax_amount = flt(_item_wise_tax_amount, precision("tax_amount", tax))
		if (tax_detail && tax_detail[key])
			item_wise_tax_amount += flt(
				tax.item_wise_tax_detail[key][1], precision("tax_amount", tax)
			)

		tax_detail[key] = [tax_rate, flt(item_wise_tax_amount, precision("base_tax_amount", tax))];
    };
}

function is_version_greater_or_equal(current, target) {
	if (!current) return false;

	// If current is an object (some older Frappe configs stored it as object)
	if (typeof current === "object" && current.version) {
		current = current.version;
	}

	// Clean beta/alpha suffix e.g "15.10.1-beta" -> "15.10.1"
	current = String(current).split("-")[0];
	target = String(target).split("-")[0];

    const c = current.split(".").map(Number);
    const t = target.split(".").map(Number);

    for (let i = 0; i < Math.max(c.length, t.length); i++) {
        const cv = c[i] || 0;
        const tv = t[i] || 0;

        if (cv > tv) return true;
        if (cv < tv) return false;
    }

    return true; // equal
}
