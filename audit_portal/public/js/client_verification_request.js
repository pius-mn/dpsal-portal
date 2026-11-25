function showCredentialPassword(message) {
	const dialog = new frappe.ui.Dialog({
		title: __("Credential password"),
		fields: [
			{
				fieldtype: "Data",
				fieldname: "portal_name",
				label: __("Portal"),
				read_only: 1,
				default: message.portal_name || "",
			},
			{
				fieldtype: "Data",
				fieldname: "username",
				label: __("Username"),
				read_only: 1,
				default: message.username || "",
			},
			{
				fieldtype: "Data",
				fieldname: "password",
				label: __("Password"),
				read_only: 1,
				default: message.password || "",
			},
			{
				fieldtype: "HTML",
				fieldname: "audit_notice",
				options: `<p class="text-muted small">${__(
					"This reveal was recorded in the request and Customer activity timeline."
				)}</p>`,
			},
		],
		primary_action_label: __("Close"),
		primary_action() {
			dialog.hide()
		},
	})
	dialog.show()
}

function revealCredential(credentialName) {
	frappe.call({
		method: "audit_portal.api.credentials.reveal_client_credential",
		args: { credential_name: credentialName },
		freeze: true,
		freeze_message: __("Revealing credential..."),
		callback(response) {
			if (response.message) showCredentialPassword(response.message)
		},
	})
}

frappe.ui.form.on("Client Verification Request", {
	refresh(frm) {
		// Submission fields (perm level 0) are read-only for everyone.
		// Reviewers with the "Audit Document Reviewer" role may edit the
		// Review section (perm level 1) directly — Frappe enforces this
		// via its native permission system.
		if (frm.is_new()) return

		if (frm.doc.request_type === "Credential") {
			frm.set_intro(
				__(
					"To review or correct this credential, change the Review Status field to Verified, Rejected, " +
					"or Superseded and add a Reviewer Note if rejecting, then save. Use Reveal credential to view the submitted password."
				),
				"blue"
			)
			if (frm.doc.credential_reference) {
				frm.add_custom_button(__("Reveal credential"), () =>
					revealCredential(frm.doc.credential_reference)
				)
			}
		} else if (frm.doc.attachment) {
			frm.set_intro(
				__(
					"To review or correct this document, change the Review Status field to Verified, Rejected, " +
					"or Superseded and add a Reviewer Note if rejecting, then save."
				),
				"blue"
			)
		}
	},
})
