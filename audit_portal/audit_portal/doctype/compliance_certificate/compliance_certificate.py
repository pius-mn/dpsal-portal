import frappe
from frappe.model.document import Document


class ComplianceCertificate(Document):
	def validate(self):
		if self.document_title:
			master = frappe.db.get_value(
				"Client Document Master",
				self.document_title,
				["doc_type", "has_expiry", "issuing_authority", "short_alias", "is_required"],
				as_dict=True,
			)
			if master:
				if not self.doc_type and master.doc_type:
					self.doc_type = master.doc_type
				if self.has_expiry is None and master.has_expiry is not None:
					self.has_expiry = master.has_expiry
				if not self.issuing_authority and master.issuing_authority:
					self.issuing_authority = master.issuing_authority
				if not self.short_alias and master.short_alias:
					self.short_alias = master.short_alias
			else:
				frappe.get_doc(
					{
						"doctype": "Client Document Master",
						"document_title": self.document_title,
						"doc_type": self.doc_type or "Other",
						"has_expiry": self.has_expiry or 0,
						"is_required": self.is_required if self.is_required is not None else 1,
						"issuing_authority": self.issuing_authority,
						"short_alias": self.short_alias,
					}
				).insert(ignore_permissions=True)
