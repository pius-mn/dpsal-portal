import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import escape_html, now_datetime, nowdate

REVIEW_STATUSES = ("Verified", "Rejected", "Superseded")
REVIEWABLE_STATUSES = ("Pending Review",) + REVIEW_STATUSES


class ClientVerificationRequest(Document):
	def before_save(self):
		"""
		Enforce review-transition rules when a reviewer sets status via the
		perm-level-1 Review section in Desk.  All other field mutations
		(submission fields, attachment, etc.) remain read-only at perm level 0
		and are written only by the portal API (client_records.py, credentials.py)
		using ignore_permissions=True.
		"""
		if self.is_new():
			return

		prior_status = frappe.db.get_value(
			"Client Verification Request", self.name, "status"
		)

		if prior_status == self.status:
			return

		if prior_status not in REVIEWABLE_STATUSES:
			frappe.throw(
				_("This verification request has a status that cannot be reviewed."),
				frappe.ValidationError,
			)

		if self.status not in REVIEW_STATUSES:
			frappe.throw(
				_("Review status must be set to Verified, Rejected, or Superseded."),
				frappe.ValidationError,
			)

		if self.status == "Rejected" and not str(self.rejection_reason or "").strip():
			frappe.throw(
				_("Add a Reviewer Note so the client knows what to fix."),
				frappe.ValidationError,
			)

		if self.request_type != "Credential" and not self.attachment:
			frappe.throw(
				_("This verification request has no uploaded file."),
				frappe.ValidationError,
			)

		self.reviewed_by = frappe.session.user
		self.reviewed_on = now_datetime()

		if self.status in ("Verified", "Superseded"):
			self.rejection_reason = None

		if self.request_type == "Credential":
			self._mirror_review_to_credential()
		else:
			self._mirror_review_to_certificate()

		self._add_review_comment()

	def _mirror_review_to_certificate(self):
		"""Update the linked Compliance Certificate child row on the Customer."""
		from audit_portal.api.client_records import get_customer_child_record

		customer_doc, certificate = get_customer_child_record(
			self.customer, "Compliance Certificate", self.compliance_requirement
		)

		if certificate.verification_request != self.name:
			frappe.throw(
				_("This verification request is no longer current for the compliance row."),
				frappe.PermissionError,
			)

		if not certificate.is_required:
			frappe.throw(
				_("This document was not requested from the client."),
				frappe.ValidationError,
			)

		certificate.status = self.status
		certificate.verified_by = self.reviewed_by
		certificate.verified_on = self.reviewed_on
		certificate.rejection_reason = self.rejection_reason

		customer_doc.save(ignore_permissions=True)

		customer_doc.add_comment(
			"Comment",
			_("Compliance document {0}: {1}.").format(
				self.document_title, self.status.lower()
			),
		)

	def _mirror_review_to_credential(self):
		from audit_portal.api.credentials import get_customer_credential
		from audit_portal.customizations import CREDENTIAL_TABLE_FIELDNAME

		customer_doc, credential = get_customer_credential(
			self.customer, self.credential_reference
		)
		if credential.verification_request != self.name:
			frappe.throw(
				_("This verification request is no longer current for the credential row."),
				frappe.PermissionError,
			)

		credential.status = "Active" if self.status == "Verified" else self.status
		credential.reviewed_by = self.reviewed_by
		credential.reviewed_on = self.reviewed_on
		credential.reviewer_note = self.rejection_reason
		if self.status == "Verified":
			credential.last_verified_on = nowdate()
			for row in customer_doc.get(CREDENTIAL_TABLE_FIELDNAME) or []:
				if (
					row.name != credential.name
					and row.portal_name == credential.portal_name
					and row.username == credential.username
					and row.status == "Active"
				):
					row.status = "Revoked"
					row.revoked_by = frappe.session.user
					row.revoked_on = now_datetime()

		customer_doc.save(ignore_permissions=True)
		customer_doc.add_comment(
			"Comment",
			_("Credential {0}: {1}.").format(
				escape_html(credential.portal_name), self.status.lower()
			),
		)

	def _add_review_comment(self):
		decision_label = {
			"Verified": "verified",
			"Rejected": "rejected",
			"Superseded": "superseded",
		}.get(self.status, self.status.lower())
		if self.request_type == "Credential":
			activity = _("Credential verification request {0}: {1}. Portal: {2}.").format(
				self.name,
				decision_label,
				escape_html(self.credential_portal or ""),
			)
		else:
			activity = _(
				"Verification request {0}: {1}. Document: {2}."
			).format(self.name, decision_label, self.document_title)
			if self.status == "Rejected":
				activity = _("{0} Reviewer note: {1}").format(
					activity, str(self.rejection_reason or "").strip()
				)
		self.add_comment("Comment", activity)
