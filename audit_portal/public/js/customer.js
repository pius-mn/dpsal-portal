let structureConfigPromise

function getStructureConfig() {
	if (!structureConfigPromise) {
		structureConfigPromise = frappe
			.call("audit_portal.api.client_records.get_legal_structure_config")
			.then((response) => response.message)
			.catch((error) => {
				structureConfigPromise = null
				frappe.msgprint({
					title: __("Could not load legal structure options"),
					message: error.message || __("Refresh the form and try again."),
					indicator: "red",
				})
				return null
			})
	}
	return structureConfigPromise
}

function getAutoValues(frm, spec) {
	let law = spec?.law || ""
	if (frm.doc.customer_type === "JV") {
		if (frm.doc.custom_structure_subcategory === "National") {
			law = "Contract-based (no specific law)"
		} else if (frm.doc.custom_structure_subcategory === "International") {
			law = "007/2021 of 05/02/2021"
		} else {
			law = ""
		}
	}
	return { law, authority: spec?.authority || "" }
}

function setTaxonomyOptions(frm, config, autoFill) {
	const spec = config[frm.doc.customer_type]
	const subcategoryFields = [
		["custom_structure_subcategory", "sub1"],
		["custom_structure_subcategory_2", "sub2"],
		["custom_structure_subcategory_3", "sub3"],
	]
	const invalidFields = []

	for (const [fieldname, key] of subcategoryFields) {
		let options = spec?.[key] || []
		if (
			frm.doc.customer_type === "NGO" &&
			key === "sub2" &&
			frm.doc.custom_structure_subcategory === "International"
		) {
			options = []
		}
		frm.set_df_property(fieldname, "options", options.join("\n"))
		frm.toggle_display(fieldname, options.length > 0)
		if (frm.doc[fieldname] && !options.includes(frm.doc[fieldname])) {
			invalidFields.push(fieldname)
		}
	}

	return Promise.all(invalidFields.map((fieldname) => frm.set_value(fieldname, null))).then(() => {
		if (!autoFill) {
			const current = getAutoValues(frm, spec)
			frm.__auditPortalAutoValues = {
				law: frm.doc.custom_governing_law === current.law ? current.law || null : null,
				authority:
					frm.doc.custom_regulating_authority === current.authority
						? current.authority || null
						: null,
			}
			return
		}

		const tracker = frm.__auditPortalAutoValues || (frm.__auditPortalAutoValues = { law: null, authority: null })
		const next = getAutoValues(frm, spec)
		const updates = []

		if (next.law) {
			if (tracker.law && frm.doc.custom_governing_law === tracker.law && tracker.law !== next.law) {
				updates.push(frm.set_value("custom_governing_law", next.law))
			} else if (!frm.doc.custom_governing_law) {
				updates.push(frm.set_value("custom_governing_law", next.law))
			}
			tracker.law = frm.doc.custom_governing_law === next.law ? next.law : null
		}

		if (next.authority) {
			if (
				tracker.authority &&
				frm.doc.custom_regulating_authority === tracker.authority &&
				tracker.authority !== next.authority
			) {
				updates.push(frm.set_value("custom_regulating_authority", next.authority))
			} else if (!frm.doc.custom_regulating_authority) {
				updates.push(frm.set_value("custom_regulating_authority", next.authority))
			}
			tracker.authority =
				frm.doc.custom_regulating_authority === next.authority ? next.authority : null
		}
		return Promise.all(updates)
	})
}

function refreshStructureFields(frm, autoFill = false) {
	getStructureConfig().then((config) => {
		if (config) setTaxonomyOptions(frm, config, autoFill)
	})
}

function showCustomerCredentialPassword(message) {
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
					"This reveal was recorded in the Customer activity timeline."
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

function openCustomerCredentialReveal(frm) {
	const rows = (frm.doc.custom_credentials || []).filter((row) => row.name)
	if (!rows.length) return

	const dialog = new frappe.ui.Dialog({
		title: __("Reveal credential"),
		fields: [
			{
				fieldtype: "Select",
				fieldname: "credential_name",
				label: __("Credential"),
				reqd: 1,
				options: rows.map((row) => ({
					value: row.name,
					label: `${row.portal_name || __("Portal")} — ${row.username || row.name}`,
				})),
				default: rows[0].name,
			},
		],
		primary_action_label: __("Reveal"),
		primary_action(values) {
			dialog.hide()
			frappe.call({
				method: "audit_portal.api.credentials.reveal_client_credential",
				args: { credential_name: values.credential_name },
				freeze: true,
				freeze_message: __("Revealing credential..."),
				callback(response) {
					if (response.message) showCustomerCredentialPassword(response.message)
				},
			})
		},
	})
	dialog.show()
}

frappe.ui.form.on("Customer", {
	refresh(frm) {
		refreshStructureFields(frm)
		if ((frm.doc.custom_credentials || []).some((row) => row.name)) {
			frm.add_custom_button(
				__("Reveal credential"),
				() => openCustomerCredentialReveal(frm),
				__("Credentials")
			)
		}
	},
	customer_type(frm) {
		refreshStructureFields(frm, true)
	},
	custom_structure_subcategory(frm) {
		refreshStructureFields(frm, true)
	},
})

frappe.ui.form.on("Compliance Certificate", {
	document_title(frm, cdt, cdn) {
		const row = locals[cdt][cdn]
		if (!row.document_title) return

		frappe.db.get_value(
			"Client Document Master",
			row.document_title,
			["doc_type", "has_expiry", "issuing_authority", "short_alias", "is_required"],
			(result) => {
				if (!result) return
				if (result.doc_type) {
					frappe.model.set_value(cdt, cdn, "doc_type", result.doc_type)
				}
				if (result.has_expiry !== undefined) {
					frappe.model.set_value(cdt, cdn, "has_expiry", result.has_expiry)
				}
				if (result.issuing_authority) {
					frappe.model.set_value(cdt, cdn, "issuing_authority", result.issuing_authority)
				}
				if (result.short_alias) {
					frappe.model.set_value(cdt, cdn, "short_alias", result.short_alias)
				}
				if (result.is_required !== undefined) {
					frappe.model.set_value(cdt, cdn, "is_required", result.is_required)
				}
			},
		)
	},
})
