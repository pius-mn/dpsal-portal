import frappe
from frappe import _
from frappe.utils import escape_html, now_datetime
from frappe.utils.password import get_decrypted_password

from audit_portal.api.client_records import get_customer_child_record
from audit_portal.api.portal import get_current_customer
from audit_portal.customizations import CREDENTIAL_TABLE_FIELDNAME

CREDENTIAL_TYPES = ("Portal Login", "Tax Portal", "Banking", "Other")
ACCESS_LEVELS = ("Full Rights", "Admin", "Limited", "View")
CREDENTIAL_REVEAL_ROLES = ("System Manager", "Audit Document Reviewer")
SUBMISSION_FIELDS = (
	"portal_name",
	"portal_url",
	"username",
	"password",
	"credential_type",
	"access_level",
	"notes",
)
VISIBLE_FIELDS = (
	"name",
	"portal_name",
	"portal_url",
	"username",
	"credential_type",
	"access_level",
	"status",
	"source",
	"verification_request",
	"submitted_on",
	"reviewed_on",
	"reviewer_note",
)


def _clean_credential_values(values):
	if not isinstance(values, dict):
		frappe.throw(_("Provide the credential details as an object."), frappe.ValidationError)
	values = dict(values)
	clean = {field: values.get(field) for field in SUBMISSION_FIELDS if values.get(field) is not None}

	portal_name = str(clean.get("portal_name") or "").strip()
	username = str(clean.get("username") or "").strip()
	if not portal_name or len(portal_name) > 140:
		frappe.throw(_("Enter a portal name of 140 characters or fewer."), frappe.ValidationError)
	if not username or len(username) > 140:
		frappe.throw(_("Enter a username of 140 characters or fewer."), frappe.ValidationError)

	password = clean.get("password")
	if not isinstance(password, str) or not password or len(password) > 500:
		frappe.throw(_("Enter a password of 500 characters or fewer."), frappe.ValidationError)

	credential_type = clean.get("credential_type") or "Portal Login"
	if credential_type not in CREDENTIAL_TYPES:
		frappe.throw(_("Choose a valid credential type."), frappe.ValidationError)

	access_level = clean.get("access_level") or "Limited"
	if access_level not in ACCESS_LEVELS:
		frappe.throw(_("Choose a valid access level."), frappe.ValidationError)

	portal_url = str(clean.get("portal_url") or "").strip()
	if portal_url and len(portal_url) > 500:
		frappe.throw(_("Enter a portal URL of 500 characters or fewer."), frappe.ValidationError)
	if portal_url and not portal_url.startswith(("http://", "https://")):
		frappe.throw(_("Enter a portal URL starting with http:// or https://."), frappe.ValidationError)

	notes = str(clean.get("notes") or "").strip()
	if len(notes) > 2000:
		frappe.throw(_("Keep notes to 2000 characters or fewer."), frappe.ValidationError)

	return {
		"portal_name": portal_name,
		"portal_url": portal_url,
		"username": username,
		"password": password,
		"credential_type": credential_type,
		"access_level": access_level,
		"notes": notes,
	}


def get_customer_credential(customer, name):
	return get_customer_child_record(customer, "Credentials", name)


@frappe.whitelist()
def get_client_credentials():
	"""Return redacted credential request metadata for the current Customer."""
	customer = get_current_customer()
	customer_doc = frappe.get_doc("Customer", customer)
	rows = customer_doc.get(CREDENTIAL_TABLE_FIELDNAME) or []
	rows = sorted(rows, key=lambda row: row.modified or row.creation or "", reverse=True)
	return [frappe._dict({field: row.get(field) for field in VISIBLE_FIELDS}) for row in rows[:250]]


def _require_credential_reveal_access():
	user = frappe.session.user
	if user == "Administrator":
		return set(CREDENTIAL_REVEAL_ROLES) | {"Administrator"}

	roles = set(frappe.get_roles(user))
	if not roles.intersection(CREDENTIAL_REVEAL_ROLES):
		frappe.throw(_("You are not allowed to view submitted credentials."), frappe.PermissionError)
	return roles


@frappe.whitelist()
def reveal_client_credential(credential_name):
	"""Return a decrypted password only to authorized Desk staff and record the access."""
	roles = _require_credential_reveal_access()
	if not isinstance(credential_name, str) or not credential_name.strip():
		frappe.throw(_("Choose a credential to reveal."), frappe.ValidationError)

	credential_name = credential_name.strip()
	values = frappe.db.get_value(
		"Credentials",
		credential_name,
		["parent", "parenttype", "password", "portal_name", "username", "verification_request"],
		as_dict=True,
	)
	if (
		not values
		or values.parenttype != "Customer"
		or not frappe.db.exists("Customer", values.parent)
	):
		frappe.throw(_("Credential not found."), frappe.PermissionError)

	if (
		"System Manager" not in roles
		and "Audit Document Reviewer" in roles
		and (
			not values.verification_request
			or not frappe.has_permission(
				"Client Verification Request", "read", doc=values.verification_request
			)
		)
	):
		frappe.throw(_("You are not allowed to view this credential."), frappe.PermissionError)

	password = get_decrypted_password(
		"Credentials", credential_name, "password", raise_exception=False
	)
	if not password:
		frappe.throw(_("The credential password is unavailable."), frappe.ValidationError)

	audit_message = _("Credential password revealed by {0}.").format(frappe.session.user)
	frappe.get_doc("Customer", values.parent).add_comment("Comment", audit_message)
	if values.verification_request and frappe.db.exists(
		"Client Verification Request", values.verification_request
	):
		frappe.get_doc("Client Verification Request", values.verification_request).add_comment(
			"Comment", audit_message
		)

	return {
		"portal_name": values.portal_name,
		"username": values.username,
		"password": password,
	}


@frappe.whitelist()
def submit_client_credential(
	portal_name,
	username,
	password,
	portal_url=None,
	credential_type=None,
	access_level=None,
	notes=None,
):
	"""Store a client-submitted secret and create a Desk-visible verification request."""
	customer = get_current_customer()
	clean = _clean_credential_values(
		{
			"portal_name": portal_name,
			"portal_url": portal_url,
			"username": username,
			"password": password,
			"credential_type": credential_type,
			"access_level": access_level,
			"notes": notes,
		}
	)
	customer_doc = frappe.get_doc("Customer", customer)
	credential_rows = customer_doc.get(CREDENTIAL_TABLE_FIELDNAME) or []
	if any(
		row.portal_name == clean["portal_name"]
		and row.username == clean["username"]
		and row.status == "Pending Review"
		for row in credential_rows
	):
		frappe.throw(
			_("A credential for this portal is already awaiting review."),
			frappe.ValidationError,
		)

	row = customer_doc.append(
		CREDENTIAL_TABLE_FIELDNAME,
		{
			**clean,
			"status": "Pending Review",
			"source": "Client Submitted",
			"submitted_by": frappe.session.user,
			"submitted_on": now_datetime(),
		},
	)
	customer_doc.save(ignore_permissions=True)

	request = frappe.get_doc(
		{
			"doctype": "Client Verification Request",
			"customer": customer,
			"request_type": "Credential",
			"credential_reference": row.name,
			"credential_portal": clean["portal_name"],
			"credential_username": clean["username"],
			"document_title": _("Credential: {0}").format(clean["portal_name"]),
			"status": "Pending Review",
			"submitted_by": frappe.session.user,
			"submitted_on": now_datetime(),
		}
	).insert(ignore_permissions=True)

	row.verification_request = request.name
	customer_doc.save(ignore_permissions=True)

	safe_portal = escape_html(clean["portal_name"])
	request.add_comment("Comment", _("Client submitted credentials for {0}.").format(safe_portal))
	customer_doc.add_comment(
		"Comment",
		_("A credential verification request was submitted: {0} ({1}).").format(
			safe_portal, escape_html(request.name)
		),
	)
	return {
		"name": request.name,
		"credential": row.name,
		"status": "Pending Review",
		"message": _("Credentials submitted for review."),
	}
