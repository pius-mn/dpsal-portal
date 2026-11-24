import frappe
from frappe import _


def get_current_customer():
	"""
	Strictly resolve the Customer linked to the authenticated user.
	Checks:
	1. User Permission for Customer
	2. Contact linked to the User and Customer via Dynamic Link
	Denies access if unauthenticated or not mapped.
	"""
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required. Please log in."), frappe.PermissionError)

	user = frappe.session.user

	# A customer portal session must map to exactly one organization.
	user_permissions = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Customer"},
		fields=["for_value"],
		limit=2,
	)
	permitted_customers = {row.for_value for row in user_permissions if row.for_value}
	if len(permitted_customers) == 1:
		return permitted_customers.pop()
	if len(permitted_customers) > 1:
		frappe.throw(_("This account is linked to more than one customer. Ask your administrator to correct the access mapping."), frappe.PermissionError)

	# 2. Resolve via linked Contact
	linked_customer = frappe.db.sql("""
		SELECT DISTINCT dl.link_name
		FROM `tabContact` c
		JOIN `tabDynamic Link` dl ON dl.parent = c.name AND dl.parenttype = 'Contact'
		WHERE (c.email_id = %(user)s OR c.user = %(user)s)
		  AND dl.link_doctype = 'Customer'
		LIMIT 2
	""", {"user": user})

	contact_customers = {row[0] for row in linked_customer if row[0]}
	if len(contact_customers) == 1:
		return contact_customers.pop()
	if len(contact_customers) > 1:
		frappe.throw(_("This account is linked to more than one customer. Ask your administrator to correct the access mapping."), frappe.PermissionError)

	frappe.throw(
		_("Access Denied: No customer record is linked to user {0}.").format(user),
		frappe.PermissionError
	)


@frappe.whitelist()
def get_portal_data():
	"""
	Fetch all dashboard data for the authenticated client's linked Customer:
	- Customer summary
	- Submitted Quotations
	- Submitted Sales Invoices
	"""
	customer = get_current_customer()

	# Customer info
	customer_info = frappe.db.get_value(
		"Customer",
		customer,
		["name", "customer_name", "customer_group", "territory"],
		as_dict=True
	) or {"name": customer, "customer_name": customer}

	# Quotations (docstatus = 1, quotation_to = "Customer", party_name = resolved_customer)
	quotations = frappe.get_all(
		"Quotation",
		filters={
			"docstatus": 1,
			"quotation_to": "Customer",
			"party_name": customer
		},
		fields=["name", "transaction_date", "valid_till", "grand_total", "currency", "status"],
		order_by="transaction_date desc",
		ignore_permissions=True
	)

	# Sales Invoices (docstatus = 1, customer = resolved_customer)
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={
			"docstatus": 1,
			"customer": customer
		},
		fields=[
			"name",
			"posting_date",
			"due_date",
			"grand_total",
			"outstanding_amount",
			"currency",
			"status"
		],
		order_by="posting_date desc",
		ignore_permissions=True
	)

	for inv in invoices:
		inv["pdf_url"] = f"/api/method/audit_portal.api.portal.download_invoice_pdf?invoice_name={inv.name}"

	return {
		"customer": customer_info,
		"quotations": quotations,
		"invoices": invoices
	}


@frappe.whitelist()
def get_quotations():
	"""Read submitted Quotations strictly scoped to the authenticated customer."""
	customer = get_current_customer()
	return frappe.get_all(
		"Quotation",
		filters={
			"docstatus": 1,
			"quotation_to": "Customer",
			"party_name": customer
		},
		fields=["name", "transaction_date", "valid_till", "grand_total", "currency", "status"],
		order_by="transaction_date desc",
		ignore_permissions=True
	)


@frappe.whitelist()
def get_quotation_details(quotation_name):
	"""Return line details only for a submitted quotation owned by the current customer."""
	customer = get_current_customer()
	if not quotation_name:
		frappe.throw(_("Proposal name is required."), frappe.MandatoryError)
	if not frappe.db.exists("Quotation", quotation_name):
		frappe.throw(_("Proposal not found."), frappe.DoesNotExistError)

	quotation = frappe.get_doc("Quotation", quotation_name, ignore_permissions=True)
	if (
		quotation.docstatus != 1
		or quotation.quotation_to != "Customer"
		or quotation.party_name != customer
	):
		frappe.throw(_("You do not have access to this proposal."), frappe.PermissionError)

	return {
		"name": quotation.name,
		"transaction_date": str(quotation.transaction_date),
		"valid_till": str(quotation.valid_till) if quotation.valid_till else "",
		"currency": quotation.currency,
		"grand_total": quotation.grand_total,
		"status": quotation.status,
		"terms": quotation.terms or "",
		"items": [
			{
				"item_code": item.item_code,
				"item_name": item.item_name,
				"description": item.description,
				"qty": item.qty,
				"uom": item.uom,
				"rate": item.rate,
				"amount": item.amount,
			}
			for item in quotation.items
		],
	}


@frappe.whitelist()
def action_quotation(quotation_name, action):
	"""
	Records a client's response to an owned, submitted quotation.
	Strictly verifies ownership and only allows a response to an open quotation.
	"""
	customer = get_current_customer()

	if not quotation_name:
		frappe.throw(_("Quotation name is required."), frappe.MandatoryError)

	clean_action = str(action or "").strip().lower()
	if clean_action not in ("accept", "reject"):
		frappe.throw(_("Invalid action. Allowed values are 'accept' or 'reject'."))

	if not frappe.db.exists("Quotation", quotation_name):
		frappe.throw(_("Quotation {0} does not exist.").format(quotation_name), frappe.DoesNotExistError)

	quotation = frappe.get_doc("Quotation", quotation_name, ignore_permissions=True)

	# Strict customer isolation check
	if quotation.docstatus != 1 or quotation.quotation_to != "Customer" or quotation.party_name != customer:
		frappe.throw(
			_("Permission Denied: You do not have permission to act on quotation {0}.").format(quotation_name),
			frappe.PermissionError
		)

	if quotation.status != "Open":
		frappe.throw(_("This proposal has already received a response or is no longer open."))

	action_label = "accepted" if clean_action == "accept" else "declined"
	quotation.db_set("status", "Replied")
	quotation.add_comment(
		"Comment",
		_("Proposal {0} by client ({1}) via Client Portal.").format(action_label, frappe.session.user)
	)

	return {
		"status": "success",
		"quotation": quotation.name,
		"action": clean_action,
		"new_status": "Replied",
		"message": _("Your decision on proposal {0} has been recorded.").format(quotation.name)
	}


@frappe.whitelist()
def get_invoices():
	"""Read submitted Sales Invoices strictly scoped to the authenticated customer."""
	customer = get_current_customer()
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={
			"docstatus": 1,
			"customer": customer
		},
		fields=[
			"name",
			"posting_date",
			"due_date",
			"grand_total",
			"outstanding_amount",
			"currency",
			"status"
		],
		order_by="posting_date desc",
		ignore_permissions=True
	)

	for inv in invoices:
		inv["pdf_url"] = f"/api/method/audit_portal.api.portal.download_invoice_pdf?invoice_name={inv.name}"

	return invoices


@frappe.whitelist()
def get_invoice_pdf_url(invoice_name):
	"""Return the verified PDF download link for an owned, submitted Sales Invoice."""
	customer = get_current_customer()

	if not invoice_name:
		frappe.throw(_("Invoice name is required."), frappe.MandatoryError)

	if not frappe.db.exists("Sales Invoice", invoice_name):
		frappe.throw(_("Sales Invoice {0} does not exist.").format(invoice_name), frappe.DoesNotExistError)

	inv = frappe.get_doc("Sales Invoice", invoice_name, ignore_permissions=True)
	if inv.docstatus != 1 or inv.customer != customer:
		frappe.throw(
			_("Permission Denied: You do not have permission to view invoice {0}.").format(invoice_name),
			frappe.PermissionError
		)

	download_url = f"/api/method/audit_portal.api.portal.download_invoice_pdf?invoice_name={invoice_name}"
	return {
		"status": "success",
		"invoice": invoice_name,
		"pdf_url": download_url
	}


@frappe.whitelist()
def download_invoice_pdf(invoice_name):
	"""
	Secure PDF streamer for owned customer invoices.
	Enforces customer row-level scoping and streams official PDF directly.
	"""
	customer = get_current_customer()

	if not invoice_name:
		frappe.throw(_("Invoice name is required."), frappe.MandatoryError)

	if not frappe.db.exists("Sales Invoice", invoice_name):
		frappe.throw(_("Sales Invoice {0} does not exist.").format(invoice_name), frappe.DoesNotExistError)

	inv = frappe.get_doc("Sales Invoice", invoice_name, ignore_permissions=True)
	if inv.docstatus != 1 or inv.customer != customer:
		frappe.throw(
			_("Permission Denied: You do not have permission to download invoice {0}.").format(invoice_name),
			frappe.PermissionError
		)

	frappe.flags.ignore_print_permissions = True
	try:
		pdf_data = frappe.get_print("Sales Invoice", invoice_name, as_pdf=True, doc=inv, no_letterhead=0)
	finally:
		frappe.flags.ignore_print_permissions = False
	frappe.local.response.filename = f"{invoice_name}.pdf"
	frappe.local.response.filecontent = pdf_data
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def get_invoice_details(invoice_name):
	"""
	Returns detailed invoice data (items, rates, tax breakdown) for owned invoice view.
	"""
	customer = get_current_customer()

	if not invoice_name or not frappe.db.exists("Sales Invoice", invoice_name):
		frappe.throw(_("Sales Invoice not found."), frappe.DoesNotExistError)

	inv = frappe.get_doc("Sales Invoice", invoice_name, ignore_permissions=True)
	if inv.docstatus != 1 or inv.customer != customer:
		frappe.throw(
			_("Permission Denied: You do not own this invoice."),
			frappe.PermissionError
		)

	items = [
		{
			"item_code": d.item_code,
			"item_name": d.item_name,
			"description": d.description,
			"qty": d.qty,
			"rate": d.rate,
			"amount": d.amount
		}
		for d in inv.items
	]

	return {
		"name": inv.name,
		"posting_date": str(inv.posting_date),
		"due_date": str(inv.due_date) if inv.due_date else "",
		"currency": inv.currency,
		"grand_total": inv.grand_total,
		"outstanding_amount": inv.outstanding_amount,
		"status": inv.status,
		"items": items,
		"download_url": f"/api/method/audit_portal.api.portal.download_invoice_pdf?invoice_name={inv.name}"
	}
