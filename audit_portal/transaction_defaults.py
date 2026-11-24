import frappe


def set_quotation_tax_id(doc, method=None):
	if doc.get("quotation_to") != "Customer" or not doc.get("party_name"):
		doc.custom_customer_tax_id = None
		return

	doc.custom_customer_tax_id = frappe.db.get_value("Customer", doc.party_name, "tax_id")
