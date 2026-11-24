import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.model.document import Document


class ClientVerificationRequest(Document):
	def before_save(self):
		"""
		Enforce review-transition rules when a reviewer sets status via the
		perm-level-1 Review section in Desk.  All other field mutations
		(submission fields, attachment, etc.) remain read-only at perm level 0
		and are written only by the portal API (client_records.py) using
		ignore_permissions=True.
		"""
		if self.is_new():
			return

		prior_status = frappe.db.get_value(
			"Client Verification Request", self.name, "status"
		)

		# No change — nothing to validate or mirror
		if prior_status == self.status:
			return

		# Only transitions away from Pending Review are permitted through Desk
		if prior_status != "Pending Review":
			frappe.throw(
				_("This document has already been reviewed and cannot be changed again."),
				frappe.ValidationError,
			)

		if self.status not in ("Verified", "Rejected"):
			frappe.throw(
				_("Review status must be set to Verified or Rejected."),
				frappe.ValidationError,
			)

		if self.status == "Rejected" and not str(self.rejection_reason or "").strip():
			frappe.throw(
				_("Add a Reviewer Note so the client knows what to fix."),
				frappe.ValidationError,
			)

		if not self.attachment:
			frappe.throw(
				_("This verification request has no uploaded file."),
				frappe.ValidationError,
			)

		# Stamp the reviewer automatically — reviewers must not set this themselves
		self.reviewed_by = frappe.session.user
		self.reviewed_on = now_datetime()

		if self.status == "Verified":
			self.rejection_reason = None

		# Mirror outcome to the linked Compliance Certificate child row
		self._mirror_review_to_certificate()

		# Append an activity comment for the audit trail
		decision_label = "verified" if self.status == "Verified" else "rejected"
		activity = _(
			"Verification request {0}: {1}. Document: {2}."
		).format(self.name, decision_label, self.document_title)
		if self.status == "Rejected":
			activity = _("{0} Reviewer note: {1}").format(
				activity, str(self.rejection_reason or "").strip()
			)
		self.add_comment("Comment", activity)

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
