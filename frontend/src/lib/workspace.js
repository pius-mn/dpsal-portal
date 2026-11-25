export const organizationSections = [
	{ id: "details", label: "Organization details", shortLabel: "Details", doctype: "Organization Details", description: "Registration and legal details." },
	{ id: "contacts", label: "Contacts & addresses", shortLabel: "Contacts", doctype: "Contact", description: "People and addresses linked to your organization." },
	{ id: "shareholders", label: "Shareholders", doctype: "Client Shareholder", description: "Owners recorded for your organization." },
	{ id: "beneficial_owners", label: "Beneficial owners", doctype: "Client Beneficial Owner", description: "People who ultimately control the organization." },
	{ id: "board_members", label: "Board members", doctype: "Client Board Member", description: "Directors and board-level contacts." },
]

export function workspaceNavigation(items) {
	const tabs = Object.fromEntries(items.map((item) => [item.id, item]))
	const organizationItem = (section) => ({
		...tabs.organization,
		id: "organization",
		section: section.id,
		label: section.label,
		shortLabel: section.shortLabel || section.label,
		description: section.description,
	})

	return [
		{ id: "overview", label: "Overview", items: [tabs.overview] },
		{ id: "billing", label: "Billing", items: [tabs.quotations, tabs.invoices] },
		{ id: "organization", label: "Organization", items: organizationSections.map(organizationItem) },
		{ id: "compliance", label: "Compliance", items: [tabs.audit_data, tabs.tax, tabs.documents] },
		{ id: "workspace", label: "Workspace", items: [tabs.credentials, tabs.appointments] },
	]
}

export function workspaceTabs(portal) {
	const openProposals = (portal?.quotations || []).filter((item) => item.status === "Open").length
	const unpaidInvoices = (portal?.invoices || []).filter(
		(item) => Number(item.outstanding_amount || 0) > 0,
	).length

	return [
		{ id: "overview", label: "Overview", group: "Engagement", description: "See what needs your attention and find the right place to start." },
		{ id: "quotations", label: "Proposals", shortLabel: "Proposals", group: "Engagement", count: openProposals, description: "Read the scope and total, then accept or decline each proposal." },
		{ id: "invoices", label: "Invoices", group: "Engagement", count: unpaidInvoices, description: "Check what is outstanding and download copies for your records." },
		{ id: "organization", label: "Organization", group: "Dossier", description: "Keep registration, ownership, and governance details current." },
		{ id: "audit_data", label: "Audit data", group: "Dossier", description: "Record bank accounts, budgets, and service fees for the audit." },
		{ id: "tax", label: "Taxes & licences", shortLabel: "Taxes", group: "Dossier", description: "Track registrations, filing dates, and renewal details." },
		{ id: "documents", label: "Documents", group: "Dossier", description: "Upload requested evidence and follow each review." },
		{ id: "credentials", label: "Credentials", group: "Dossier", description: "Submit external portal credentials for secure review." },
		{ id: "appointments", label: "Appointments", group: "Dossier", description: "Book time with your audit team or cancel a future meeting." },
	]
}

export const workspaceIndex = [
	{
		kicker: "PROFILE",
		title: "Organization records",
		description: "Maintain registration, ownership, and board details.",
		tab: "organization",
		icon: ["M12 3a3.4 3.4 0 1 1 0 6.8A3.4 3.4 0 0 1 12 3Z", "M5 20c0-3.4 3.1-5.4 7-5.4s7 2 7 5.4"],
	},
	{
		kicker: "COMPLIANCE",
		title: "Taxes & licences",
		description: "Record filing dates and registration details.",
		tab: "tax",
		icon: ["M6 3h12v18l-3-2-3 2-3-2-3 2V3Z", "M9 8h6M9 12h6"],
	},
	{
		kicker: "EVIDENCE",
		title: "Documents & licences",
		description: "Upload evidence and follow each review.",
		tab: "documents",
		icon: ["M7 3h7l4 4v14H7V3Z", "M14 3v5h4M9 12h6M9 16h6"],
	},
	{
		kicker: "FINANCE",
		title: "Audit data",
		description: "Record bank accounts, budgets, and service fees.",
		tab: "audit_data",
		icon: ["M4 20V10m5 10V5m5 15v-7m5 7V8"],
	},
	{
		kicker: "ACCESS",
		title: "Credentials",
		description: "Share external portal logins for secure review.",
		tab: "credentials",
		icon: ["M5 10h14v10H5V10Z", "M8 10V7a4 4 0 0 1 8 0v3"],
	},
	{
		kicker: "MEETINGS",
		title: "Appointments",
		description: "Book or cancel a future meeting.",
		tab: "appointments",
		icon: ["M4 5h16v16H4V5Z", "M8 3v4M16 3v4M4 10h16"],
	},
	{
		kicker: "COMMERCIAL",
		title: "Proposals",
		description: "Read the scope and share your decision.",
		tab: "quotations",
		icon: ["M6 3h9l3 3v15H6V3Z", "M9 12h6M9 16h4"],
	},
	{
		kicker: "BILLING",
		title: "Invoices",
		description: "Check the balance or download a copy.",
		tab: "invoices",
		icon: ["M6 2h12v20l-3-2-3 2-3-2-3 2V2Z", "M9 7h6M9 11h6M9 15h3"],
	},
]
