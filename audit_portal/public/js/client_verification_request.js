frappe.ui.form.on("Client Verification Request", {
	refresh(frm) {
		// Submission fields (perm level 0) are read-only for everyone.
		// Reviewers with the "Audit Document Reviewer" role may edit the
		// Review section (perm level 1) directly — Frappe enforces this
		// via its native permission system.  No custom action buttons needed.
		if (frm.is_new()) return

		if (frm.doc.status === "Pending Review" && frm.doc.attachment) {
			frm.set_intro(
				__(
					"To review this document, change the Review Status field to Verified or Rejected " +
					"and add a Reviewer Note if rejecting, then save."
				),
				"blue"
			)
		}
	},
})
