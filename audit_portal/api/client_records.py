import os

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime, nowdate, validate_email_address
from frappe.utils.file_manager import save_file
from frappe.contacts.doctype.address.address import get_default_address

from audit_portal.api.portal import get_current_customer
from audit_portal.legal_structure import (
	STRUCTURE_TAXONOMY,
	default_document_rows,
	structure_defaults,
)


PROFILE_CUSTOM_FIELDS = {
	"customer_type": "customer_type",
	"structure_subcategory": "custom_structure_subcategory",
	"structure_subcategory_2": "custom_structure_subcategory_2",
	"structure_subcategory_3": "custom_structure_subcategory_3",
	"structure_details": "custom_structure_details",
	"governing_law": "custom_governing_law",
	"regulating_authority": "custom_regulating_authority",
	"registration_no": "custom_registration_no",
	"domicile": "custom_domicile",
	"registration_date": "custom_registration_date",
	"regulator_reg_date": "custom_regulator_reg_date",
	"regulator_dereg_date": "custom_regulator_dereg_date",
	"special_attention": "custom_special_attention",
}

RECORD_FIELDS = {
	"Client Bank Account": (
		"bank_name",
		"account_number",
		"branch_name",
		"branch_address",
		"branch_email",
		"branch_phone",
		"account_type",
		"sub_category",
		"currency",
		"swift_bic",
		"operation_method",
		"signatories",
		"date_open",
		"date_close",
		"rel_manager",
		"rel_email",
		"rel_mobile",
		"has_online",
		"online_limit",
		"online_timing",
		"limits",
	),
	"Client Budget Line": (
		"budget_line",
		"budget_period",
		"currency",
		"monthly_budget",
		"annual_budget",
		"actual_spend",
		"operated_by",
		"payment_due",
		"penalty_interest",
		"credit_facility",
		"remarks",
	),
	"Client Shareholder": (
		"member_name",
		"person_nature",
		"domicile",
		"id_reg_no",
		"share_category",
		"share_pct",
		"shares",
		"share_price",
		"member_since",
		"phone",
		"email",
		"is_board",
	),
	"Client Board Member": (
		"member_name",
		"person",
		"resident_in_rwanda",
		"designation_regulator",
		"designation_internal",
		"since",
		"executive",
		"role",
		"phone",
		"email",
	),
	"Client Beneficial Owner": (
		"bo_name",
		"domicile",
		"person",
		"id_reg_no",
		"ownership_form",
		"ownership_pct",
		"owner_since",
		"phone",
		"email",
		"is_board",
	),
	"Client Tax Registration": (
		"tax_type",
		"applies_to",
		"rate",
		"exempted",
		"frequency",
		"period",
		"due_date",
		"declared_date",
		"payment_date",
		"reg_date",
		"dereg_date",
		"financial_year",
		"facility_applied",
		"why_not",
		"remarks",
	),
}

CUSTOMER_TABLE_FIELDS = {
	"Client Bank Account": "custom_bank_accounts",
	"Client Budget Line": "custom_budget_lines",
	"Client Shareholder": "custom_shareholders",
	"Client Board Member": "custom_board_members",
	"Client Beneficial Owner": "custom_beneficial_owners",
	"Client Tax Registration": "custom_tax_registrations",
	"Compliance Certificate": "custom_compliance_certificates",
}

LIST_FIELDS = {
	"Client Bank Account": (
		"name",
		"bank_name",
		"account_number",
		"account_type",
		"branch_name",
		"currency",
		"swift_bic",
		"date_open",
		"date_close",
		"has_online",
	),
	"Client Budget Line": (
		"name",
		"budget_line",
		"budget_period",
		"currency",
		"monthly_budget",
		"annual_budget",
		"actual_spend",
		"payment_due",
	),
	"Client Shareholder": (
		"name",
		"member_name",
		"person_nature",
		"share_pct",
		"shares",
		"member_since",
	),
	"Client Board Member": (
		"name",
		"member_name",
		"designation_internal",
		"executive",
		"since",
		"email",
	),
	"Client Beneficial Owner": (
		"name",
		"bo_name",
		"ownership_form",
		"ownership_pct",
		"owner_since",
		"email",
	),
	"Client Tax Registration": (
		"name",
		"tax_type",
		"frequency",
		"due_date",
		"declared_date",
		"payment_date",
	),
	"Compliance Certificate": (
		"name",
		"document_title",
		"doc_type",
		"doc_number",
		"expiry_date",
		"has_expiry",
		"attachment",
		"status",
		"rejection_reason",
		"is_required",
	),
}

CONTACT_FIELDS = ("first_name", "last_name", "designation", "department", "email", "phone")
ADDRESS_FIELDS = (
	"address_title",
	"address_type",
	"address_line1",
	"address_line2",
	"city",
	"state",
	"pincode",
	"country",
	"email_id",
	"phone",
	"is_primary_address",
)


def _clean_values(doctype, values):
	if not isinstance(values, dict):
		frappe.throw(_("Provide the record details as an object."), frappe.ValidationError)
	allowed_fields = RECORD_FIELDS[doctype]
	clean_values = {
		field: value
		for field, value in values.items()
		if field in allowed_fields and value is not None
	}
	for field in ("email", "branch_email", "rel_email"):
		if clean_values.get(field):
			validate_email_address(clean_values[field], throw=True)
	for field in ("share_pct", "ownership_pct"):
		if field not in clean_values or clean_values[field] in ("", None):
			continue
		try:
			percentage = float(clean_values[field])
		except (TypeError, ValueError):
			frappe.throw(_("Enter a valid ownership percentage."), frappe.ValidationError)
		if not 0 <= percentage <= 100:
			frappe.throw(_("Ownership percentage must be between 0 and 100."), frappe.ValidationError)
	if doctype in {"Client Bank Account", "Client Budget Line"}:
		currency = clean_values.get("currency")
		if currency and not frappe.db.exists("Currency", currency):
			frappe.throw(_("Choose a valid currency."), frappe.ValidationError)
	return clean_values


def _linked_record_customer_links(doctype, name):
	return frappe.get_all(
		"Dynamic Link",
		filters={"parent": name, "parenttype": doctype, "parentfield": "links"},
		fields=["link_doctype", "link_name"],
	)


def _get_owned_linked_record(doctype, name, customer):
	if not name or not frappe.db.exists(doctype, name):
		frappe.throw(_("Record not found."), frappe.DoesNotExistError)
	links = _linked_record_customer_links(doctype, name)
	if len(links) != 1 or links[0].link_doctype != "Customer" or links[0].link_name != customer:
		frappe.throw(_("This record is shared or does not belong to your organization."), frappe.PermissionError)
	return frappe.get_doc(doctype, name)


def _get_linked_records(doctype, customer, fields):
	links = frappe.get_all(
		"Dynamic Link",
		filters={
			"parenttype": doctype,
			"parentfield": "links",
			"link_doctype": "Customer",
			"link_name": customer,
		},
		fields=["parent"],
		limit=500,
	)
	names = list(dict.fromkeys(row.parent for row in links))
	records = []
	for name in names:
		doc = frappe.get_doc(doctype, name)
		record = {field: doc.get(field) for field in fields}
		record.update(
			{
				"name": doc.name,
				"can_edit": len(_linked_record_customer_links(doctype, doc.name)) == 1,
			}
		)
		records.append(record)
	return records


def _clean_linked_values(doctype, values):
	if not isinstance(values, dict):
		frappe.throw(_("Provide the record details as an object."), frappe.ValidationError)
	allowed_fields = CONTACT_FIELDS if doctype == "Contact" else ADDRESS_FIELDS
	clean_values = {field: value for field, value in values.items() if field in allowed_fields and value is not None}
	if doctype == "Contact":
		if not str(clean_values.get("first_name") or "").strip():
			frappe.throw(_("Enter the contact's first name."), frappe.ValidationError)
		if clean_values.get("email"):
			validate_email_address(clean_values["email"], throw=True)
		if clean_values.get("phone"):
			clean_values["phone"] = str(clean_values["phone"]).strip()
		return clean_values

	if "is_primary_address" in clean_values:
		is_primary = clean_values["is_primary_address"]
		if is_primary not in (True, False, 0, 1, "0", "1"):
			frappe.throw(_("Choose whether this is the primary billing address."), frappe.ValidationError)
		clean_values["is_primary_address"] = is_primary in (True, 1, "1")

	for field in ("address_title", "address_type", "address_line1", "city", "country"):
		if not str(clean_values.get(field) or "").strip():
			frappe.throw(_("Complete the required address fields."), frappe.ValidationError)
	if not frappe.db.exists("Country", clean_values["country"]):
		frappe.throw(_("Choose a valid country."), frappe.ValidationError)
	if clean_values.get("email_id"):
		validate_email_address(clean_values["email_id"], throw=True)
	return clean_values


def _save_linked_record(doctype, name, values, customer):
	if name:
		doc = _get_owned_linked_record(doctype, name, customer)
	else:
		doc = frappe.new_doc(doctype)
		doc.append("links", {"link_doctype": "Customer", "link_name": customer})
	clean_values = _clean_linked_values(doctype, values)
	customer_doc = frappe.get_doc("Customer", customer) if doctype == "Address" else None
	current_primary_address = None
	is_primary_address = None

	if doctype == "Address":
		current_primary_address = (
			customer_doc.customer_primary_address or get_default_address("Customer", customer)
		)
		is_primary_address = clean_values.pop("is_primary_address", None)
		if is_primary_address is None:
			is_primary_address = bool(doc.is_primary_address)
		if not current_primary_address and doc.is_new():
			is_primary_address = True

	if doctype == "Contact":
		email = clean_values.pop("email", "")
		phone = clean_values.pop("phone", "")
		doc.update(clean_values)
		doc.set("email_ids", [{"email_id": email, "is_primary": 1}] if email else [])
		doc.set("phone_nos", [{"phone": phone, "is_primary_phone": 1}] if phone else [])
	else:
		doc.update(clean_values)
		if doctype == "Address":
			doc.is_primary_address = is_primary_address

	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)

	if doctype == "Address" and (is_primary_address or current_primary_address == doc.name):
		customer_doc.customer_primary_address = doc.name if is_primary_address else None
		if not is_primary_address:
			customer_doc.primary_address = None
		customer_doc.save(ignore_permissions=True)

	return doc


def get_customer_child_record(customer, doctype, name):
	fieldname = CUSTOMER_TABLE_FIELDS.get(doctype)
	if not fieldname or not name:
		frappe.throw(_("Record not found."), frappe.DoesNotExistError)
	customer_doc = frappe.get_doc("Customer", customer)
	for row in customer_doc.get(fieldname) or []:
		if row.name == name:
			return customer_doc, row
	frappe.throw(_("This record does not belong to your organization."), frappe.PermissionError)


def _save_customer_record(doctype, name, values, customer):
	clean_values = _clean_values(doctype, values)
	table_field = CUSTOMER_TABLE_FIELDS[doctype]
	if name:
		customer_doc, doc = get_customer_child_record(customer, doctype, name)
	else:
		customer_doc = frappe.get_doc("Customer", customer)
		doc = customer_doc.append(table_field, {})
	doc.update(clean_values)
	customer_doc.save(ignore_permissions=True)
	return doc


@frappe.whitelist()
def get_client_records():
	"""Return a client dossier using only the customer mapped to this session."""
	customer = get_current_customer()
	customer_fields = [
		"name",
		"tax_id",
		*(PROFILE_CUSTOM_FIELDS.values()),
	]
	customer_field_values = frappe.db.get_value("Customer", customer, customer_fields, as_dict=True)
	customer_details = {
		"name": customer,
		"tax_id": customer_field_values.tax_id,
		**{
			fieldname: customer_field_values.get(custom_field)
			for fieldname, custom_field in PROFILE_CUSTOM_FIELDS.items()
		},
	}

	customer_doc = frappe.get_doc("Customer", customer)
	records = {}
	for doctype, fields in LIST_FIELDS.items():
		table_field = CUSTOMER_TABLE_FIELDS[doctype]
		child_rows = customer_doc.get(table_field) or []
		if doctype == "Compliance Certificate":
			child_rows = [
				row for row in child_rows if row.is_required or row.attachment
			]
		child_rows = sorted(
			child_rows,
			key=lambda row: row.modified or row.creation or "",
			reverse=True,
		)[:250]
		records[doctype] = [
			frappe._dict({field: row.get(field) for field in fields}) for row in child_rows
		]
		for row in records[doctype]:
			if doctype == "Compliance Certificate":
				row["download_url"] = (
					f"/api/method/audit_portal.api.client_records.download_compliance_file"
					f"?certificate_name={row.name}"
					if row.attachment
					else None
				)

	contacts = _get_linked_records(
		"Contact",
		customer,
		["first_name", "last_name", "designation", "department", "email_id", "phone"],
	)
	for contact in contacts:
		contact["email"] = contact.pop("email_id")

	return {
		"customer": customer,
		"customer_name": frappe.db.get_value("Customer", customer, "customer_name") or customer,
		"customer_details": customer_details,
		"customer_types": (
			frappe.get_meta("Customer").get_field("customer_type").options or ""
		).splitlines(),
		"legal_structure_config": STRUCTURE_TAXONOMY,
		"records": records,
		"currencies": frappe.get_all(
			"Currency",
			fields=["name"],
			order_by="name asc",
			limit=500,
		),
		"contacts": contacts,
		"addresses": _get_linked_records(
			"Address",
			customer,
			[
				"address_title",
				"address_type",
				"address_line1",
				"address_line2",
				"city",
				"state",
				"pincode",
				"country",
				"email_id",
				"phone",
				"is_primary_address",
			],
		),
		"countries": frappe.get_all("Country", pluck="name", order_by="name asc", limit=500),
		"appointments": _get_appointments(customer),
	}


@frappe.whitelist()
def save_customer_details(values):
	customer = get_current_customer()
	if not isinstance(values, dict):
		frappe.throw(_("Provide the organization details as an object."), frappe.ValidationError)
	values = dict(values)
	tax_id = values.pop("tax_id", None)
	legacy_tin = values.pop("tin", None)
	if tax_id is None:
		tax_id = legacy_tin
	elif legacy_tin is not None and legacy_tin != tax_id:
		frappe.throw(_("Provide the tax identification number only once."), frappe.ValidationError)
	clean_values = {
		fieldname: value
		for fieldname, value in values.items()
		if fieldname in PROFILE_CUSTOM_FIELDS and value is not None
	}
	customer_values = {
		PROFILE_CUSTOM_FIELDS[fieldname]: value for fieldname, value in clean_values.items()
	}
	customer_type = customer_values.get("customer_type")
	if customer_type:
		valid_types = (frappe.get_meta("Customer").get_field("customer_type").options or "").splitlines()
		if customer_type not in valid_types:
			frappe.throw(_("Choose a valid customer type."), frappe.ValidationError)
	if tax_id is not None:
		if not isinstance(tax_id, str):
			frappe.throw(_("Enter a valid tax identification number."), frappe.ValidationError)
		customer_values["tax_id"] = tax_id.strip()
	if customer_values:
		customer_doc = frappe.get_doc("Customer", customer)
		if "customer_type" in customer_values:
			old_defaults = structure_defaults(
				customer_doc.customer_type, customer_doc.custom_structure_subcategory
			)
			new_defaults = structure_defaults(
				customer_values["customer_type"],
				customer_values.get(
					"custom_structure_subcategory", customer_doc.custom_structure_subcategory
				),
			)
			for fieldname, key in (
				("custom_governing_law", "law"),
				("custom_regulating_authority", "authority"),
			):
				current_value = customer_doc.get(fieldname)
				old_default = old_defaults[key]
				new_default = new_defaults[key]
				if (
					fieldname not in customer_values
					and old_default
					and new_default
					and old_default != new_default
					and current_value == old_default
				):
					customer_values[fieldname] = new_default
		customer_doc.update(customer_values)
		customer_doc.save(ignore_permissions=True)
	return {"name": customer, "message": _("Organization details saved.")}


@frappe.whitelist()
def get_legal_structure_config():
	return STRUCTURE_TAXONOMY


@frappe.whitelist()
def add_default_compliance_requirements(customer):
	customer_doc = frappe.get_doc("Customer", customer)
	customer_doc.check_permission("write")

	certificates = customer_doc.get(CUSTOMER_TABLE_FIELDS["Compliance Certificate"]) or []
	existing_titles = {row.document_title for row in certificates}
	rows = default_document_rows(customer_doc.customer_type)
	created = 0
	for row in rows:
		if row["document_title"] in existing_titles:
			continue
		customer_doc.append(CUSTOMER_TABLE_FIELDS["Compliance Certificate"], row)
		existing_titles.add(row["document_title"])
		created += 1
	if created:
		customer_doc.save(ignore_permissions=True)

	return {
		"created": created,
		"message": _("Added {0} suggested document requirement(s).").format(created),
	}


@frappe.whitelist()
def save_client_record(doctype, values, name=None):
	customer = get_current_customer()
	if doctype not in RECORD_FIELDS:
		frappe.throw(_("This record type is not available in the client workspace."), frappe.PermissionError)
	record = _save_customer_record(doctype, name, values, customer)
	return {"name": record.name, "message": _("Changes saved.")}


@frappe.whitelist()
def save_customer_linked_record(doctype, values, name=None):
	customer = get_current_customer()
	if doctype not in ("Contact", "Address"):
		frappe.throw(_("This record type is not available in the client workspace."), frappe.PermissionError)
	record = _save_linked_record(doctype, name, values, customer)
	return {"name": record.name, "message": _("Changes saved.")}


def _get_owned_certificate(certificate_name, customer):
	return get_customer_child_record(customer, "Compliance Certificate", certificate_name)


@frappe.whitelist()
def upload_compliance_file(certificate_name):
	customer = get_current_customer()
	customer_doc, certificate = _get_owned_certificate(certificate_name, customer)
	if not certificate.is_required:
		frappe.throw(_("This document has not been requested by your audit team."), frappe.PermissionError)
	uploaded_file = frappe.request.files.get("file")
	if not uploaded_file or not uploaded_file.filename:
		frappe.throw(_("Choose a file to upload."), frappe.ValidationError)

	filename = os.path.basename(uploaded_file.filename)
	extension = os.path.splitext(filename)[1].lower()
	if extension not in {".pdf", ".png", ".jpg", ".jpeg"}:
		frappe.throw(_("Upload a PDF, PNG, or JPEG document."), frappe.ValidationError)

	content = uploaded_file.read(10 * 1024 * 1024 + 1)
	if len(content) > 10 * 1024 * 1024:
		frappe.throw(_("The file is larger than 10 MB."), frappe.ValidationError)
	if not content:
		frappe.throw(_("The selected file is empty."), frappe.ValidationError)

	previous_request = certificate.verification_request
	if previous_request and frappe.db.exists("Client Verification Request", previous_request):
		previous = frappe.get_doc("Client Verification Request", previous_request)
		if previous.status == "Pending Review":
			previous.status = "Superseded"
			previous.save(ignore_permissions=True)
			previous.add_comment(
				"Comment",
				_("This submission was superseded by a newer client upload."),
			)

	request = frappe.get_doc(
		{
			"doctype": "Client Verification Request",
			"customer": customer,
			"compliance_requirement": certificate.name,
			"document_title": certificate.document_title,
			"status": "Pending Review",
			"submitted_by": frappe.session.user,
			"submitted_on": now_datetime(),
		}
	).insert(ignore_permissions=True)
	file_doc = save_file(
		fname=filename,
		content=content,
		dt="Client Verification Request",
		dn=request.name,
		is_private=1,
		df="attachment",
	)
	request.attachment = file_doc.file_url
	request.save(ignore_permissions=True)
	certificate.update(
		{
			"attachment": file_doc.file_url,
			"last_updated": nowdate(),
			"status": "Pending Review",
			"submitted_by": request.submitted_by,
			"submitted_on": request.submitted_on,
			"verified_by": None,
			"verified_on": None,
			"rejection_reason": None,
			"verification_request": request.name,
		}
	)
	customer_doc.save(ignore_permissions=True)
	request.add_comment(
		"Comment",
		_("Client uploaded {0} for verification.").format(
			frappe.utils.escape_html(certificate.document_title)
		),
	)
	customer_doc.add_comment(
		"Comment",
		_("A new verification request was submitted: {0} ({1}).").format(
			frappe.utils.escape_html(certificate.document_title),
			frappe.utils.escape_html(request.name),
		),
	)
	return {
		"name": request.name,
		"message": _("Document uploaded for review."),
		"status": "Pending Review",
	}


@frappe.whitelist()
def download_compliance_file(certificate_name):
	customer = get_current_customer()
	_, certificate = _get_owned_certificate(certificate_name, customer)
	if not certificate.attachment:
		frappe.throw(_("No file has been uploaded for this document."), frappe.DoesNotExistError)

	verification_request = certificate.verification_request
	if verification_request:
		request = frappe.get_doc("Client Verification Request", verification_request)
		if request.customer != customer or request.compliance_requirement != certificate.name:
			frappe.throw(
				_("This verification file does not belong to your organization."),
				frappe.PermissionError,
			)
		attachment = request.attachment
		file_filters = {"file_url": attachment, "is_private": 1}
	else:
		attachment = certificate.attachment
		file_filters = {
			"file_url": attachment,
			"attached_to_doctype": "Customer",
			"attached_to_name": customer,
			"attached_to_field": CUSTOMER_TABLE_FIELDS["Compliance Certificate"],
			"is_private": 1,
		}
	if not attachment:
		frappe.throw(_("No file has been uploaded for this document."), frappe.DoesNotExistError)

	file_doc = frappe.db.get_value(
		"File",
		file_filters,
		["name", "is_private"],
		as_dict=True,
	)
	if not file_doc or not file_doc.is_private:
		frappe.throw(_("The private document file could not be found."), frappe.DoesNotExistError)
	file_doc = frappe.get_doc("File", file_doc.name)
	frappe.local.response.filename = os.path.basename(attachment)
	frappe.local.response.filecontent = file_doc.get_content()
	frappe.local.response.type = "download"


def _get_appointments(customer):
	if not frappe.db.exists("DocType", "Appointment"):
		return []
	fields = ["name", "scheduled_time", "status", "customer_details"]
	if frappe.get_meta("Appointment").has_field("appointment_purpose"):
		fields.append("appointment_purpose")
	rows = frappe.get_all(
		"Appointment",
		filters={"party": customer, "appointment_with": "Customer"},
		fields=fields,
		order_by="scheduled_time asc",
		limit=100,
		ignore_permissions=True,
	)
	return [
		{
			"name": row.name,
			"scheduled_time": row.scheduled_time,
			"status": row.status,
			"purpose": row.get("appointment_purpose"),
			"notes": row.customer_details,
		}
		for row in rows
	]


@frappe.whitelist()
def book_client_appointment(date, time, purpose=None, notes=None):
	customer = get_current_customer()
	try:
		scheduled_time = get_datetime(f"{date} {time}")
	except (TypeError, ValueError):
		frappe.throw(_("Choose a valid date and time."), frappe.ValidationError)
	if scheduled_time <= now_datetime():
		frappe.throw(_("Choose a future date and time."), frappe.ValidationError)

	customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
	customer_email = frappe.db.get_value("Customer", customer, "email_id") or frappe.session.user
	fields = {
		"doctype": "Appointment",
		"scheduled_time": scheduled_time,
		"customer_name": customer_name,
		"customer_email": customer_email,
		"customer_details": (notes or "").strip(),
		"party": customer,
		"appointment_with": "Customer",
		"created_through_portal": 0,
	}
	if frappe.get_meta("Appointment").has_field("appointment_purpose"):
		fields["appointment_purpose"] = (purpose or "").strip()

	original_session = {
		"user": frappe.session.user,
		"sid": frappe.session.sid,
		"data": frappe.session.data,
	}
	try:
		frappe.set_user("Administrator")
		appointment = frappe.get_doc(fields).insert(ignore_permissions=True)
	finally:
		frappe.local.session.user = original_session["user"]
		frappe.local.session.sid = original_session["sid"]
		frappe.local.session.data = original_session["data"]
	return {"name": appointment.name, "message": _("Appointment booked.")}


@frappe.whitelist()
def cancel_client_appointment(name):
	customer = get_current_customer()
	if not name or not frappe.db.exists("Appointment", name):
		frappe.throw(_("Appointment not found."), frappe.DoesNotExistError)
	appointment = frappe.get_doc("Appointment", name)
	if appointment.party != customer or appointment.appointment_with != "Customer":
		frappe.throw(_("This appointment does not belong to your organization."), frappe.PermissionError)
	if appointment.status == "Closed":
		return {"message": _("This appointment is already cancelled.")}
	if get_datetime(appointment.scheduled_time) < now_datetime():
		frappe.throw(_("Past appointments cannot be cancelled."), frappe.ValidationError)
	appointment.status = "Closed"
	appointment.save(ignore_permissions=True)
	return {"message": _("Appointment cancelled.")}
