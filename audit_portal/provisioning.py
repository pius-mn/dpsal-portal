import frappe
from frappe import _


def ensure_audit_client_role():
	"""Ensure the 'Audit Client' role exists with Website User (desk_access=0)."""
	if not frappe.db.exists("Role", "Audit Client"):
		role = frappe.get_doc({
			"doctype": "Role",
			"role_name": "Audit Client",
			"desk_access": 0,
			"is_custom": 0
		})
		role.insert(ignore_permissions=True)
	else:
		frappe.db.set_value("Role", "Audit Client", "desk_access", 0)


def ensure_audit_document_reviewer_role():
	"""Ensure the Desk role used to assign document-verification access exists."""
	if not frappe.db.exists("Role", "Audit Document Reviewer"):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": "Audit Document Reviewer",
				"desk_access": 1,
				"is_custom": 1,
			}
		).insert(ignore_permissions=True)


def ensure_default_document_masters():
	"""Seed standard document types into Client Document Master catalog."""
	if not frappe.db.exists("DocType", "Client Document Master"):
		return

	from audit_portal.legal_structure import DEFAULT_DOCUMENT_SET, STRUCTURE_EXTRA_DOCUMENTS

	all_docs = list(DEFAULT_DOCUMENT_SET)
	for extras in STRUCTURE_EXTRA_DOCUMENTS.values():
		all_docs.extend(extras)

	seen = set()
	for title, doc_type, has_expiry in all_docs:
		if title in seen:
			continue
		seen.add(title)
		if not frappe.db.exists("Client Document Master", title):
			frappe.get_doc(
				{
					"doctype": "Client Document Master",
					"document_title": title,
					"doc_type": doc_type,
					"has_expiry": has_expiry,
					"is_required": 1,
				}
			).insert(ignore_permissions=True)

	# Backfill any titles already used on existing Compliance Certificate rows
	if frappe.db.table_exists("Compliance Certificate"):
		existing_titles = frappe.db.sql_list(
			"""SELECT DISTINCT document_title FROM `tabCompliance Certificate`
			WHERE document_title IS NOT NULL AND document_title != ''"""
		)
		for title in existing_titles:
			if title and not frappe.db.exists("Client Document Master", title):
				frappe.get_doc(
					{
						"doctype": "Client Document Master",
						"document_title": title,
						"doc_type": "Other",
						"is_required": 1,
					}
				).insert(ignore_permissions=True)




def validate_signup_request(doc, method=None):
	"""Enforce that only System Manager (or Administrator) can approve signup requests."""
	if doc.approval_status == "Approved":
		prev_status = None
		if not doc.is_new():
			prev_status = frappe.db.get_value("Client Signup Request", doc.name, "approval_status")

		# If transitioning to Approved from non-approved or on initial insert as Approved
		if prev_status != "Approved":
			current_roles = frappe.get_roles()
			is_admin_user = (frappe.session.user == "Administrator")
			has_manager_role = ("System Manager" in current_roles)

			if not (is_admin_user or has_manager_role):
				frappe.throw(
					_("Only a System Manager can transition signup request status to Approved."),
					frappe.PermissionError
				)


def on_update_signup_request(doc, method=None):
	"""Provision Customer, User, and User Permission when request is marked Approved."""
	if doc.approval_status == "Approved":
		provision_client_for_signup_request(doc)


def provision_client_for_signup_request(doc):
	"""
	Atomically and idempotently provisions:
	1. Customer record (or link existing if matched by name).
	2. User record (Website User, Audit Client role, send_welcome_email = 1).
	3. User Permission (user -> allow Customer -> for_value customer, apply_to_all_doctypes = 1).
	4. Links customer and portal_user back to the Client Signup Request.
	"""
	ensure_audit_client_role()

	# 1. Resolve or Create Customer
	customer_name = None
	if doc.customer and frappe.db.exists("Customer", doc.customer):
		customer_name = doc.customer
	else:
		existing_customer = frappe.db.get_value("Customer", {"customer_name": doc.company_name}, "name")
		if existing_customer:
			customer_name = existing_customer
		else:
			customer_group = frappe.db.get_single_value("Selling Settings", "customer_group")
			if not customer_group or frappe.db.get_value("Customer Group", customer_group, "is_group"):
				customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"

			territory = frappe.db.get_single_value("Selling Settings", "territory")
			if not territory or frappe.db.get_value("Territory", territory, "is_group"):
				territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "Kenya"

			customer = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": doc.company_name,
				"customer_type": "Company",
				"customer_group": customer_group,
				"territory": territory
			})
			customer.insert(ignore_permissions=True)
			customer_name = customer.name

	# 2. Resolve or Create User
	portal_user = None
	if doc.portal_user and frappe.db.exists("User", doc.portal_user):
		portal_user = doc.portal_user
		user = frappe.get_doc("User", portal_user)
	else:
		existing_user = frappe.db.get_value("User", {"email": doc.email}, "name")
		if existing_user:
			portal_user = existing_user
			user = frappe.get_doc("User", portal_user)
		else:
			send_email = 0 if (frappe.flags.in_test or getattr(frappe.flags, "mute_emails", False)) else 1
			user = frappe.get_doc({
				"doctype": "User",
				"email": doc.email,
				"first_name": doc.contact_name,
				"phone": doc.phone or None,
				"user_type": "Website User",
				"send_welcome_email": send_email,
				"roles": [{"role": "Audit Client"}]
			})
			user.insert(ignore_permissions=True)
			portal_user = user.name

	# Ensure User has Audit Client role
	user_roles = [r.role for r in user.roles]
	if "Audit Client" not in user_roles:
		user.append("roles", {"role": "Audit Client"})
		user.save(ignore_permissions=True)

	# 3. Provision User Permission
	existing_perm = frappe.db.exists("User Permission", {
		"user": portal_user,
		"allow": "Customer",
		"for_value": customer_name
	})
	if not existing_perm:
		user_perm = frappe.get_doc({
			"doctype": "User Permission",
			"user": portal_user,
			"allow": "Customer",
			"for_value": customer_name,
			"apply_to_all_doctypes": 1
		})
		user_perm.insert(ignore_permissions=True)

	# 4. Link back to Client Signup Request
	if doc.customer != customer_name or doc.portal_user != portal_user:
		frappe.db.set_value(
			"Client Signup Request",
			doc.name,
			{
				"customer": customer_name,
				"portal_user": portal_user
			},
			update_modified=False
		)
		doc.customer = customer_name
		doc.portal_user = portal_user

	return {
		"customer": customer_name,
		"portal_user": portal_user
	}
