async function setCustomerTaxId(frm) {
	const fieldname = "custom_customer_tax_id"
	if (!frm.fields_dict[fieldname]) return

	const customer = frm.doc.quotation_to === "Customer" ? frm.doc.party_name : null
	if (!customer) {
		await frm.set_value(fieldname, "")
		return
	}

	const result = await frappe.db.get_value("Customer", customer, "tax_id")
	if (frm.doc.quotation_to === "Customer" && frm.doc.party_name === customer) {
		await frm.set_value(fieldname, result.message?.tax_id || "")
	}
}

frappe.ui.form.on("Quotation", {
	refresh(frm) {
		if (frm.is_new() && frm.doc.party_name) setCustomerTaxId(frm)
	},
	quotation_to(frm) {
		setCustomerTaxId(frm)
	},
	party_name(frm) {
		setCustomerTaxId(frm)
	},
})
