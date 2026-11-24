export function workspaceTabs(portal) {
	return [
		{ id: "overview", label: "Overview", group: "Engagement", description: "See what needs your attention and find the right place to start." },
		{ id: "quotations", label: "Proposals", shortLabel: "Proposals", group: "Engagement", count: portal?.quotations?.length || 0, description: "Read the scope and total, then accept or decline each proposal." },
		{ id: "invoices", label: "Invoices", group: "Engagement", count: portal?.invoices?.length || 0, description: "Check what is outstanding and download copies for your records." },
		{ id: "organization", label: "Organization", group: "Dossier", description: "Keep registration, ownership, and governance details current." },
		{ id: "audit_data", label: "Audit data", group: "Dossier", description: "Record bank accounts, budgets, and service fees for the audit." },
		{ id: "tax", label: "Taxes & licences", shortLabel: "Taxes", group: "Dossier", description: "Track registrations, filing dates, and renewal details." },
		{ id: "documents", label: "Documents", group: "Dossier", description: "Upload requested evidence and follow each review." },
		{ id: "appointments", label: "Appointments", group: "Dossier", description: "Book time with your audit team or cancel a future meeting." },
	]
}

export const workspaceIndex = [
	{ kicker: "Profile", title: "Organization records", description: "Maintain registration, ownership, and board details.", tab: "organization" },
	{ kicker: "Evidence", title: "Documents & licences", description: "Upload evidence and follow each review.", tab: "documents" },
	{ kicker: "Compliance", title: "Taxes & licences", description: "Record filing dates and registration details.", tab: "tax" },
	{ kicker: "Finance", title: "Audit data", description: "Record bank accounts, budgets, and service fees.", tab: "audit_data" },
	{ kicker: "Commercial", title: "Proposals", description: "Read the scope and share your decision.", tab: "quotations" },
	{ kicker: "Billing", title: "Invoices", description: "Check the balance or download a copy.", tab: "invoices" },
	{ kicker: "Meetings", title: "Appointments", description: "Book or cancel a future meeting.", tab: "appointments" },
]
