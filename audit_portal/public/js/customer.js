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

frappe.ui.form.on("Customer", {
	refresh(frm) {
		refreshStructureFields(frm)
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
