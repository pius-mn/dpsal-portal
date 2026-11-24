import { options } from "./format"

export const appointmentFields = [
	{ name: "date", label: "Date", type: "date", required: true },
	{ name: "time", label: "Time", type: "time", required: true },
	{ name: "purpose", label: "What would you like to discuss?", placeholder: "For example, annual filing or an audit question", maxlength: 140 },
	{ name: "notes", label: "Additional details", type: "textarea", maxlength: 2000 },
]

export const contactFields = [
	{ name: "first_name", label: "First name", required: true },
	{ name: "last_name", label: "Last name" },
	{ name: "designation", label: "Job title" },
	{ name: "department", label: "Department" },
	{ name: "email", label: "Email address", type: "email" },
	{ name: "phone", label: "Phone number", type: "tel" },
]

export const signupFields = [
	{ name: "company_name", label: "Organization name", required: true, autocomplete: "organization", maxlength: 140, placeholder: "e.g. Acme Corporation" },
	{ name: "contact_name", label: "Primary contact", required: true, autocomplete: "name", maxlength: 140, placeholder: "Full name" },
	{ name: "email", label: "Business email", type: "email", required: true, autocomplete: "email", maxlength: 140, placeholder: "name@organization.com" },
	{ name: "phone", label: "Phone number", type: "tel", autocomplete: "tel", maxlength: 40, placeholder: "+250 700 000 000" },
	{ name: "notes", label: "What should our team know?", type: "textarea", maxlength: 2000, rows: 3, placeholder: "Audit timing, scope, or requirements" },
].map((field) => ({ inputProps: { size: "lg", variant: "outline" }, ...field }))

export const governanceTypes = ["Client Shareholder", "Client Beneficial Owner", "Client Board Member"]
export const auditRecordTypes = ["Client Bank Account", "Client Budget Line"]

export function addressFields(workspace) {
	return [
		{ name: "address_title", label: "Address name", required: true, placeholder: "For example, Main office" },
		{ name: "address_type", label: "Address type", type: "select", required: true, options: options(["Billing", "Shipping", "Office", "Personal", "Plant", "Postal", "Shop", "Subsidiary", "Warehouse", "Current", "Permanent", "Other"]) },
		{ name: "is_primary_address", label: "Use as the billing address for new quotations and invoices", type: "checkbox" },
		{ name: "address_line1", label: "Address line 1", required: true },
		{ name: "address_line2", label: "Address line 2" },
		{ name: "city", label: "City or town", required: true },
		{ name: "state", label: "State or province" },
		{ name: "pincode", label: "Postal code" },
		{ name: "country", label: "Country", type: "select", required: true, options: options(workspace?.countries || []) },
		{ name: "email_id", label: "Address email", type: "email" },
		{ name: "phone", label: "Address phone", type: "tel" },
	]
}

export function customerFields(workspace) {
	return [
		{ name: "customer_type", label: "Legal structure", type: "select", options: options(workspace?.customer_types || []) },
		{
			name: "structure_subcategory",
			label: "Structure sub-category",
			type: "select",
			dependsOn: ["customer_type"],
			optionsByValue: subcategoryOptions(workspace, "sub1"),
		},
		{
			name: "structure_subcategory_2",
			label: "Structure sub-category 2",
			type: "select",
			dependsOn: ["customer_type", "structure_subcategory"],
			optionsByValue: subcategoryOptions(workspace, "sub2"),
			optionsOverride: {
				when: { customer_type: "NGO", structure_subcategory: "International" },
				options: [],
			},
		},
		{
			name: "structure_subcategory_3",
			label: "Structure sub-category 3",
			type: "select",
			dependsOn: ["customer_type"],
			optionsByValue: subcategoryOptions(workspace, "sub3"),
		},
		{ name: "structure_details", label: "Additional structure details" },
		{
			name: "governing_law",
			label: "Governing law",
			autoDefaultByValue: Object.fromEntries(
				Object.entries(workspace?.legal_structure_config || {}).map(([structure, spec]) => [
					structure,
					structure === "JV" ? "" : spec.law || "",
				]),
			),
			autoDefaultOverrides: [
				{
					when: { customer_type: "JV", structure_subcategory: "National" },
					value: "Contract-based (no specific law)",
				},
				{
					when: { customer_type: "JV", structure_subcategory: "International" },
					value: "007/2021 of 05/02/2021",
				},
			],
			autoDefaultFor: ["customer_type", "structure_subcategory"],
		},
		{
			name: "regulating_authority",
			label: "Regulating authority",
			type: "select",
			options: options(["RDB", "RGB", "RCA", "RRA", "Notary", "None"]),
			autoDefaultByValue: Object.fromEntries(
				Object.entries(workspace?.legal_structure_config || {}).map(([structure, spec]) => [
					structure,
					spec.authority || "",
				]),
			),
			autoDefaultFor: ["customer_type"],
		},
		{ name: "registration_no", label: "Registration number" },
		{ name: "tax_id", label: "Tax identification number" },
		{ name: "domicile", label: "Domicile", type: "select", options: options(["National", "International"]) },
		{ name: "registration_date", label: "Registration date", type: "date" },
		{ name: "regulator_reg_date", label: "Regulator registration date", type: "date" },
		{ name: "regulator_dereg_date", label: "Regulator deregistration date", type: "date" },
		{ name: "special_attention", label: "Notes for your audit team", type: "textarea", maxlength: 2000 },
	]
}

export function buildRecordDefinitions(workspace) {
	const currencies = options(workspace?.currencies || [])
	const withCurrency = (definition) => ({
		...definition,
		fields: definition.fields.map((field) => (field.name === "currency" ? { ...field, options: currencies } : field)),
	})

	return {
		Contact: { title: "Contacts", fields: contactFields },
		Address: { title: "Addresses", fields: addressFields(workspace) },
		"Client Shareholder": {
			title: "Shareholders",
			titleField: "member_name",
			emptyTitle: "No shareholders added",
			emptyDescription: "Add the people or organizations that hold shares in your organization.",
			fields: [
				{ name: "member_name", label: "Shareholder name", required: true },
				{ name: "person_nature", label: "Person type", type: "select", options: options(["Natural Person", "Body Incorporate"]) },
				{ name: "domicile", label: "Domicile", type: "select", options: options(["National", "International"]) },
				{ name: "id_reg_no", label: "ID or registration number" },
				{ name: "share_category", label: "Share category" },
				{ name: "share_pct", label: "Ownership percentage", type: "number", step: "0.01" },
				{ name: "shares", label: "Number of shares", type: "number", step: "1" },
				{ name: "share_price", label: "Share value", type: "number", step: "0.01" },
				{ name: "member_since", label: "Member since", type: "date" },
				{ name: "phone", label: "Phone" },
				{ name: "email", label: "Email", type: "email" },
				{ name: "is_board", label: "Board role", type: "select", options: options(["No", "Yes", "Executive"]) },
			],
		},
		"Client Beneficial Owner": {
			title: "Beneficial owners",
			titleField: "bo_name",
			emptyTitle: "No beneficial owners added",
			emptyDescription: "List the individuals who ultimately own or control your organization.",
			fields: [
				{ name: "bo_name", label: "Beneficial owner name", required: true },
				{ name: "domicile", label: "Domicile", type: "select", options: options(["National", "International"]) },
				{ name: "person", label: "Person type", type: "select", options: options(["Natural Person", "Body Incorporate"]) },
				{ name: "id_reg_no", label: "ID or registration number" },
				{ name: "ownership_form", label: "Ownership form" },
				{ name: "ownership_pct", label: "Ownership percentage", type: "number", step: "0.01" },
				{ name: "owner_since", label: "Owner since", type: "date" },
				{ name: "phone", label: "Phone" },
				{ name: "email", label: "Email", type: "email" },
				{ name: "is_board", label: "Is a board member", type: "checkbox" },
			],
		},
		"Client Board Member": {
			title: "Board members",
			titleField: "member_name",
			emptyTitle: "No board members added",
			emptyDescription: "Add current directors and board members so your organization record stays up to date.",
			fields: [
				{ name: "member_name", label: "Member name", required: true },
				{ name: "person", label: "Person type", type: "select", options: options(["Natural Person", "Body Incorporate"]) },
				{ name: "resident_in_rwanda", label: "Resident in Rwanda", type: "select", options: options(["Yes", "No"]) },
				{ name: "designation_regulator", label: "Registered designation" },
				{ name: "designation_internal", label: "Internal designation" },
				{ name: "since", label: "Appointed on", type: "date" },
				{ name: "executive", label: "Board role", type: "select", options: options(["Executive", "Non-Executive"]) },
				{ name: "role", label: "Role" },
				{ name: "phone", label: "Phone" },
				{ name: "email", label: "Email", type: "email" },
			],
		},
		"Client Tax Registration": {
			title: "Tax registrations",
			titleField: "tax_type",
			emptyTitle: "No tax registrations added",
			emptyDescription: "Record the tax types, filing frequency, and next dates your organization tracks.",
			fields: [
				{ name: "tax_type", label: "Tax type", required: true },
				{ name: "applies_to", label: "Applies to this organization", type: "select", options: options(["Yes", "No"]) },
				{ name: "rate", label: "Rate" },
				{ name: "exempted", label: "Tax exempt", type: "select", options: options(["Yes", "No"]) },
				{ name: "frequency", label: "Filing frequency", type: "select", options: options(["Fortnightly", "Monthly", "Quarterly", "Annually"]) },
				{ name: "period", label: "Current period" },
				{ name: "due_date", label: "Next filing due", type: "date" },
				{ name: "declared_date", label: "Last declared", type: "date" },
				{ name: "payment_date", label: "Last payment date", type: "date" },
				{ name: "reg_date", label: "Registration date", type: "date" },
				{ name: "dereg_date", label: "Deregistration date", type: "date" },
				{ name: "financial_year", label: "Financial year" },
				{ name: "facility_applied", label: "Tax facility" },
				{ name: "why_not", label: "Reason if not applicable", type: "textarea" },
				{ name: "remarks", label: "Notes", type: "textarea" },
			],
		},
		"Client Bank Account": withCurrency({
			title: "Client bank accounts",
			titleField: "bank_name",
			emptyTitle: "No bank accounts recorded",
			emptyDescription: "Record the bank accounts your organization uses for audit work. Do not enter online banking passwords or card numbers.",
			fields: [
				{ name: "bank_name", label: "Bank", required: true },
				{ name: "account_number", label: "Account number" },
				{ name: "branch_name", label: "Branch" },
				{ name: "branch_address", label: "Branch address", type: "textarea" },
				{ name: "branch_email", label: "Branch email", type: "email" },
				{ name: "branch_phone", label: "Branch phone", type: "tel" },
				{ name: "account_type", label: "Account type", type: "select", options: options(["Checking", "Saving", "Current", "Other"]) },
				{ name: "sub_category", label: "Account category", type: "select", options: options(["Main", "Sub"]) },
				{ name: "currency", label: "Currency", type: "select", options: currencies },
				{ name: "swift_bic", label: "SWIFT/BIC" },
				{ name: "operation_method", label: "Signing arrangement", type: "select", options: options(["Jointly", "Severally"]) },
				{ name: "signatories", label: "Authorized signatories", type: "textarea" },
				{ name: "date_open", label: "Date opened", type: "date" },
				{ name: "date_close", label: "Date closed", type: "date" },
				{ name: "rel_manager", label: "Relationship manager" },
				{ name: "rel_email", label: "Manager email", type: "email" },
				{ name: "rel_mobile", label: "Manager phone", type: "tel" },
				{ name: "has_online", label: "Online banking available", type: "select", options: options(["Yes", "No"]) },
				{ name: "online_limit", label: "Online transaction limit", type: "number", step: "0.01" },
				{ name: "online_timing", label: "Online limit period" },
				{ name: "limits", label: "Account transaction limit", type: "number", step: "0.01" },
			],
		}),
		"Client Budget Line": withCurrency({
			title: "Client budget and spending",
			titleField: "budget_line",
			emptyTitle: "No budget lines recorded",
			emptyDescription: "Enter the client's budget lines and actual spending for the period under review.",
			fields: [
				{ name: "budget_line", label: "Budget line", required: true },
				{ name: "budget_period", label: "Budget period", placeholder: "For example, FY2026 or January 2026" },
				{ name: "currency", label: "Currency", type: "select", options: currencies },
				{ name: "monthly_budget", label: "Monthly budget", type: "number", step: "0.01" },
				{ name: "annual_budget", label: "Annual budget", type: "number", step: "0.01" },
				{ name: "actual_spend", label: "Actual spend", type: "number", step: "0.01" },
				{ name: "operated_by", label: "Operated by" },
				{ name: "payment_due", label: "Next payment due", type: "date" },
				{ name: "penalty_interest", label: "Penalty and interest", type: "number", step: "0.01" },
				{ name: "credit_facility", label: "Supplier credit facility" },
				{ name: "remarks", label: "Notes", type: "textarea" },
			],
		}),
		"Compliance Certificate": {
			title: "Documents and licences",
			emptyTitle: "No documents recorded",
			emptyDescription: "Your audit team has not requested any documents yet.",
		},
	}
}

function subcategoryOptions(workspace, key) {
	return Object.fromEntries(
		Object.entries(workspace?.legal_structure_config || {}).map(([structure, spec]) => [
			structure,
			options(spec[key] || []),
		]),
	)
}
