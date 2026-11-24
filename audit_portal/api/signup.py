import frappe
from frappe import _
from frappe.utils import validate_email_address


@frappe.whitelist(allow_guest=True)
def submit_signup_request(company_name, contact_name, email, phone=None, notes=None):
	"""
	Public endpoint for guest signups (/signup).
	Validates input, enforces rate limiting and duplicate email checks.
	Creates a Client Signup Request record strictly in 'Pending' status.
	Never provisions live Customer or User records directly.
	"""
	# 1. Rate limiting by IP (max 10 submissions per 10 minutes)
	ip = getattr(frappe.local, "request_ip", None) or "127.0.0.1"
	cache_key = f"audit_portal_signup_limit:{ip}"
	recent_attempts = frappe.cache.get_value(cache_key) or 0
	if recent_attempts >= 10:
		frappe.throw(
			_("Too many signup attempts from your IP. Please try again in 10 minutes."),
			frappe.TooManyRequestsError
		)
	frappe.cache.set_value(cache_key, recent_attempts + 1, expires_in_sec=600)

	# 2. Input sanitization & validation
	if not company_name or not str(company_name).strip():
		frappe.throw(_("Company Name is required."), frappe.MandatoryError)
	if not contact_name or not str(contact_name).strip():
		frappe.throw(_("Contact Name is required."), frappe.MandatoryError)
	if not email or not str(email).strip():
		frappe.throw(_("Email address is required."), frappe.MandatoryError)

	clean_company = str(company_name).strip()
	clean_contact = str(contact_name).strip()
	clean_email = str(email).strip().lower()
	clean_phone = str(phone).strip() if phone else None
	clean_notes = str(notes).strip() if notes else None

	# Validate email format
	validate_email_address(clean_email, throw=True)

	# 3. Duplicate checks
	if frappe.db.exists("Client Signup Request", {"email": clean_email}):
		frappe.throw(
			_("A signup request for email '{0}' already exists and is being reviewed.").format(clean_email),
			frappe.DuplicateEntryError
		)

	if frappe.db.exists("User", clean_email):
		frappe.throw(
			_("An account for email '{0}' already exists. Please log in directly.").format(clean_email),
			frappe.DuplicateEntryError
		)

	# 4. Create staging request strictly as 'Pending'
	signup_doc = frappe.get_doc({
		"doctype": "Client Signup Request",
		"company_name": clean_company,
		"contact_name": clean_contact,
		"email": clean_email,
		"phone": clean_phone,
		"notes": clean_notes,
		"approval_status": "Pending"
	})
	signup_doc.insert(ignore_permissions=True)

	return {
		"status": "success",
		"message": _("Your signup request has been submitted successfully and is pending administrator review."),
		"name": signup_doc.name
	}
