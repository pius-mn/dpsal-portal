<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { Button, FrappeUIProvider } from "frappe-ui"
import DialogFrame from "../components/DialogFrame.vue"
import KeyValueList from "../components/KeyValueList.vue"
import NoticeBar from "../components/NoticeBar.vue"
import PortalHeader from "../components/PortalHeader.vue"
import ResponsiveLedger from "../components/ResponsiveLedger.vue"
import SheetHeader from "../components/SheetHeader.vue"
import StatePanel from "../components/StatePanel.vue"
import StatusPill from "../components/StatusPill.vue"
import { formatCurrency, formatDate } from "../lib/format"
import { createPortalResource, fetchResource } from "../lib/resources"
import { organizationSections, workspaceIndex, workspaceTabs } from "../lib/workspace"

const ClientRecordsWorkspace = defineAsyncComponent(() => import("./ClientRecordsWorkspace.vue"))

const user = document.querySelector("#app")?.dataset.user || "Guest"
const portalResource = createPortalResource("audit_portal.api.portal.get_portal_data")
const recordsResource = createPortalResource("audit_portal.api.client_records.get_client_records")
const credentialsResource = createPortalResource("audit_portal.api.credentials.get_client_credentials")
const quotationDetailsResource = createPortalResource("audit_portal.api.portal.get_quotation_details")
const quotationActionResource = createPortalResource("audit_portal.api.portal.action_quotation", { method: "POST" })
const invoiceDetailsResource = createPortalResource("audit_portal.api.portal.get_invoice_details")

const portal = computed(() => portalResource.data)
const recordsData = ref(null)
const credentialRows = ref(null)
const loading = computed(() => portalResource.loading || (!portalResource.fetched && !portalResource.error))
const refreshing = computed(() => portalResource.loading && portalResource.fetched)
const activeTab = ref("overview")
const activeSubTab = ref("details")
const loadError = ref("")
const alert = ref(null)
const activeQuotation = computed(() => (quotationActionResource.loading && selectedQuotation.value ? selectedQuotation.value.name : ""))
const selectedQuotation = ref(null)
const quotationAction = ref("")
const quotationDialogOpen = ref(false)
const quotationDetails = ref(null)
const quotationDetailsError = ref("")
const quotationDetailsLoading = computed(() => quotationDetailsResource.loading)
const quotationDetailsDialogOpen = ref(false)
const invoiceDetails = ref(null)
const invoiceError = ref("")
const invoiceLoading = computed(() => invoiceDetailsResource.loading)
const invoiceDialogOpen = ref(false)

const tabs = computed(() => workspaceTabs(portal.value))
const activeSection = computed(() => tabs.value.find((tab) => tab.id === activeTab.value) || tabs.value[0])
const isDossierTab = computed(() => activeSection.value.group === "Dossier")
const entityName = computed(() => portal.value?.customer?.customer_name || portal.value?.customer?.name || "DP SAL Portal")

const quotationColumns = [
	{ key: "name", label: "Proposal", cellClass: "cell-ref" },
	{ key: "transaction_date", label: "Received", cellClass: "cell-muted whitespace-nowrap" },
	{ key: "valid_till", label: "Reply by", cellClass: "cell-muted whitespace-nowrap" },
	{ key: "grand_total", label: "Total", cellClass: "cell-num cell-strong" },
	{ key: "status", label: "Status" },
	{ key: "choice", label: "Your choice", headerClass: "text-right", cellClass: "text-right" },
]

const invoiceColumns = [
	{ key: "name", label: "Invoice", cellClass: "cell-ref" },
	{ key: "posting_date", label: "Invoice date", cellClass: "cell-muted whitespace-nowrap" },
	{ key: "due_date", label: "Pay by", cellClass: "cell-muted whitespace-nowrap" },
	{ key: "grand_total", label: "Total", cellClass: "cell-num cell-strong" },
	{ key: "outstanding_amount", label: "Still to pay", cellClass: "cell-num" },
	{ key: "status", label: "Status" },
	{ key: "options", label: "Options", headerClass: "text-right", cellClass: "text-right" },
]

const openQuotations = computed(() =>
	(portal.value?.quotations || []).filter((quotation) => quotation.status === "Open"),
)

const unpaidInvoices = computed(() =>
	(portal.value?.invoices || []).filter((invoice) => Number(invoice.outstanding_amount || 0) > 0),
)

const unpaidTotalLabel = computed(() => {
	if (!unpaidInvoices.value.length) return "None due"
	const currencies = new Set(unpaidInvoices.value.map((invoice) => invoice.currency || "USD"))
	if (currencies.size !== 1) return `${unpaidInvoices.value.length} invoices`
	const total = unpaidInvoices.value.reduce((sum, invoice) => sum + Number(invoice.outstanding_amount || 0), 0)
	return formatCurrency(total, [...currencies][0])
})

function recordCount(doctype) {
	return recordsData.value?.records?.[doctype]?.length || 0
}

const dossierChecks = computed(() => {
	if (!recordsData.value) return null
	const details = recordsData.value.customer_details || {}
	return {
		details: Boolean(details.customer_type && (details.registration_no || details.structure_details)),
		contacts: Boolean((recordsData.value.contacts?.length || 0) && (recordsData.value.addresses?.length || 0)),
		shareholders: recordCount("Client Shareholder") > 0,
		beneficial_owners: recordCount("Client Beneficial Owner") > 0,
		board_members: recordCount("Client Board Member") > 0,
	}
})

const dossierCompletion = computed(() => {
	const checks = dossierChecks.value
	if (!checks) return { complete: 0, total: 5, available: false }
	return {
		complete: Object.values(checks).filter(Boolean).length,
		total: 5,
		available: true,
	}
})

const dossierCompletionLabel = computed(() =>
	dossierCompletion.value.available
		? `${dossierCompletion.value.complete}/${dossierCompletion.value.total} complete`
		: "—",
)

const pendingDocuments = computed(() =>
	(recordsData.value?.records?.["Compliance Certificate"] || []).filter(
		(row) => row.status === "Pending Review",
	).length,
)

const tileStats = computed(() => ({
	organization: dossierCompletionLabel.value,
	tax: recordsData.value ? `${recordCount("Client Tax Registration")} on file` : "—",
	documents: recordsData.value ? `${pendingDocuments.value} pending` : "—",
	audit_data: recordsData.value
		? `${recordCount("Client Bank Account") + recordCount("Client Budget Line")} records`
		: "—",
	credentials: credentialRows.value ? `${credentialRows.value.length} submitted` : "—",
	appointments: recordsData.value ? `${recordsData.value.appointments?.length || 0} booked` : "—",
	quotations: `${openQuotations.value.length} open`,
	invoices: `${unpaidInvoices.value.length} unpaid`,
}))

function tileStatus(entry) {
	return tileStats.value[entry.tab] || "—"
}

const nextAction = computed(() => {
	if (!portal.value) return null
	if (unpaidInvoices.value.length) {
		return {
			title: "You have an unpaid balance",
			description: "Open your invoices to review the balance and download a copy.",
			action: "View invoices",
			tab: "invoices",
		}
	}
	if (openQuotations.value.length) {
		return {
			title: "A proposal is ready for your decision",
			description: "Review the scope and total, then accept or decline the proposal.",
			action: "Review proposal",
			tab: "quotations",
		}
	}
	if (dossierCompletion.value.available && dossierCompletion.value.complete < dossierCompletion.value.total) {
		return {
			title: "A few dossier sections need attention",
			description: `${dossierCompletionLabel.value} across your organization record. Add what is missing when you have the details.`,
			action: "Complete organization",
			tab: "organization",
		}
	}
	return {
		title: "All caught up",
		description: "Your invoices, proposals, and organization sections are up to date.",
		action: "",
		tab: "",
	}
})

const coverLedger = computed(() => [
	{ label: "Proposals to review", value: openQuotations.value.length, note: "Waiting for your decision" },
	{ label: "Unpaid balance", value: unpaidTotalLabel.value, note: "Across your invoices" },
	{ label: "Dossier completion", value: dossierCompletion.value.available ? `${dossierCompletion.value.complete}/${dossierCompletion.value.total}` : "—", note: "Sections complete" },
])

const dossierDetails = computed(() => [
	{ label: "Organization", value: portal.value?.customer?.customer_name || portal.value?.customer?.name || "—" },
	{ label: "Registration / tax PIN", value: recordsData.value?.customer_details?.registration_no || "—" },
	{ label: "Signed in as", value: user },
])

const invoiceUrl = computed(() => invoiceDetails.value?.download_url || "")

async function loadMetrics() {
	const [recordsResult, credentialsResult] = await Promise.allSettled([
		fetchResource(recordsResource, null, "We couldn’t load your workspace totals."),
		fetchResource(credentialsResource, null, "We couldn’t load your credential totals."),
	])
	recordsData.value = recordsResult.status === "fulfilled" ? recordsResult.value : null
	credentialRows.value = credentialsResult.status === "fulfilled" ? credentialsResult.value : null
}

async function loadPortal() {
	loadError.value = ""
	try {
		await fetchResource(
			portalResource,
			null,
			"We couldn’t open your workspace. Check that you’re signed in with the client account approved by your audit team, then try again.",
		)
		await loadMetrics()
	} catch (error) {
		loadError.value = error.message
	}
}

function showAlert(type, message) {
	alert.value = { type, message }
}

function requestQuotationDecision(quotation, action) {
	selectedQuotation.value = quotation
	quotationAction.value = action
	quotationDetailsDialogOpen.value = false
	quotationDialogOpen.value = true
}

async function openQuotation(quotation) {
	selectedQuotation.value = quotation
	quotationDetails.value = null
	quotationDetailsError.value = ""
	quotationDetailsDialogOpen.value = true
	try {
		quotationDetails.value = await fetchResource(
			quotationDetailsResource,
			{ quotation_name: quotation.name },
			"We couldn’t load this proposal. Close this window and try again.",
		)
	} catch (error) {
		quotationDetailsError.value = error.message
	}
}

async function confirmQuotationDecision() {
	if (!selectedQuotation.value || !quotationAction.value) return
	const quotation = selectedQuotation.value
	const action = quotationAction.value
	try {
		const result = await fetchResource(
			quotationActionResource,
			{ quotation_name: quotation.name, action },
			"We couldn’t record your choice. Please try again.",
		)
		quotation.status = result.new_status
		showAlert("success", result.message)
		quotationDialogOpen.value = false
		selectedQuotation.value = null
	} catch (error) {
		showAlert("error", error.message)
	}
}

async function openInvoice(invoice) {
	invoiceDetails.value = null
	invoiceError.value = ""
	invoiceDialogOpen.value = true
	try {
		invoiceDetails.value = await fetchResource(
			invoiceDetailsResource,
			{ invoice_name: invoice.name },
			"We couldn’t load this invoice. Close this window and try again.",
		)
	} catch (error) {
		invoiceError.value = error.message
	}
}

function goToLogin() {
	window.location.assign("/login?redirect-to=/client-portal")
}

function scrollToTop() {
	const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches
	window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" })
}

function isValidSection(section) {
	return organizationSections.some((item) => item.id === section)
}

function openTab(tab, { replace = false, skipScroll = false, section = "" } = {}) {
	const id = tabs.value.some((item) => item.id === tab) ? tab : "overview"
	const nextSection = id === "organization" && isValidSection(section) ? section : "details"
	const url = new URL(window.location.href)
	if (id === "overview") url.searchParams.delete("tab")
	else url.searchParams.set("tab", id)
	if (nextSection === "details") url.searchParams.delete("section")
	else url.searchParams.set("section", nextSection)

	if (activeTab.value !== id || activeSubTab.value !== nextSection || replace) {
		window.history[replace ? "replaceState" : "pushState"]({ tab: id, section: nextSection }, "", url)
		activeTab.value = id
		activeSubTab.value = nextSection
	}
	if (!skipScroll) scrollToTop()
}

function syncTabFromUrl({ skipScroll = true } = {}) {
	const params = new URLSearchParams(window.location.search)
	const requested = params.get("tab")
	if (!requested || !tabs.value.some((item) => item.id === requested)) {
		if (requested || params.has("section")) {
			const url = new URL(window.location.href)
			url.searchParams.delete("tab")
			url.searchParams.delete("section")
			window.history.replaceState({ tab: "overview", section: "details" }, "", url)
		}
		activeTab.value = "overview"
		activeSubTab.value = "details"
		return
	}
	openTab(requested, { replace: true, skipScroll, section: params.get("section") || "" })
}

function handleNavigate(id, section) {
	openTab(id, { section })
}

function openOrganizationSection(section) {
	openTab("organization", { section })
}

function onPopState() {
	syncTabFromUrl()
}

watch(
	activeTab,
	(tab) => {
		const section = tabs.value.find((item) => item.id === tab)
		document.title = `${section?.label || "Client dossier"} · DP SAL Portal`
	},
	{ immediate: true },
)

onMounted(() => {
	syncTabFromUrl()
	window.addEventListener("popstate", onPopState)
	loadPortal()
})
onBeforeUnmount(() => window.removeEventListener("popstate", onPopState))
</script>

<template>
	<FrappeUIProvider>
		<div class="min-h-screen font-sans text-ink">
			<PortalHeader
				:user="user"
				context="portal"
				:nav-items="tabs"
				:active-nav="activeTab"
				:active-section="activeSubTab"
				:entity-name="entityName"
				@navigate="handleNavigate"
			/>

			<main id="portal-content" tabindex="-1" class="outline-none">
				<div v-if="loading && !portal" class="shell-max">
					<StatePanel label="Loading portal" message="Opening your workspace…" />
				</div>

				<div v-else-if="loadError" class="shell-max">
					<StatePanel tone="error" :message="loadError" label="Access problem" eyebrow="Access problem">
						<template #title>
							<h1 id="access-title" class="sheet-title mt-2">Let’s get you to the right account.</h1>
						</template>
						<p class="mt-2 text-sm leading-6 text-slate-500">If you’ve just been approved, your audit team may still need to finish linking your account.</p>
						<template #actions>
							<Button class="audit-btn audit-btn--primary" @click="loadPortal()">Try again</Button>
							<Button class="audit-btn audit-btn--secondary" @click="goToLogin">Sign in again</Button>
							<a href="/signup" class="text-action self-center">Request access</a>
						</template>
					</StatePanel>
				</div>

				<template v-else-if="portal">
					<div v-if="activeTab !== 'overview'" class="shell-max mt-5">
						<div class="flex flex-wrap items-center justify-between gap-3 border-y border-line bg-paper/70 px-[1.1rem] py-2.5">
							<p class="eyebrow flex min-w-0 items-center">
								<span>Client</span>
								<span class="mx-2 text-line-strong" aria-hidden="true">/</span>
								<span class="truncate text-ink-soft">{{ entityName }}</span>
							</p>
							<button class="text-action" @click="openTab('overview')"><span class="mr-1" aria-hidden="true">←</span>Back to overview</button>
						</div>
					</div>

					<div class="shell-max">
						<section v-if="activeTab === 'overview'" class="dossier-cover" aria-labelledby="workspace-title">
							<div class="grid grid-cols-1 items-start gap-8 min-[960px]:grid-cols-[minmax(0,1.35fr)_minmax(18rem,0.65fr)]">
								<div>
									<p class="eyebrow eyebrow--light">Client dossier · {{ portal.customer.name }}</p>
									<h1 id="workspace-title" class="mt-3.5 max-w-[20ch] text-balance font-display text-[clamp(2.5rem,6vw,4.4rem)] font-normal leading-[0.96] tracking-[-0.02em] text-[#f8fbf9]">{{ portal.customer.customer_name || portal.customer.name }}</h1>
									<p class="mt-[1.1rem] max-w-[44ch] text-base leading-[1.65] text-[#e9f2ed]/70">See what needs your attention, review proposals, and find your invoices. If you’re unsure what to do, start with the next step.</p>
								</div>
								<aside class="rounded-[0.9rem] border border-brass/40 bg-bottle-deep/95 px-[1.3rem] pb-[1.35rem] pt-[1.25rem] backdrop-blur-sm max-sm:p-[1.1rem]" aria-labelledby="next-step-heading">
									<p class="eyebrow eyebrow--light">Your next step</p>
									<h2 id="next-step-heading" class="mt-2 font-display text-2xl font-normal leading-[1.12] text-[#f8fbf9]">{{ nextAction.title }}</h2>
									<p class="mt-2 text-[0.8125rem] leading-[1.6] text-[#e9f2ed]/70">{{ nextAction.description }}</p>
									<Button v-if="nextAction.tab" class="audit-btn audit-btn--brass mt-[1.15rem]" @click="openTab(nextAction.tab)">
										{{ nextAction.action }}
									</Button>
								</aside>
							</div>

							<KeyValueList variant="cover" :items="coverLedger">
								<template #value="{ item }">
									{{ item.value }}
									<p class="font-sans">{{ item.note }}</p>
								</template>
							</KeyValueList>
						</section>

						<header v-else class="mt-6 border-b border-line pb-6" aria-labelledby="section-heading">
							<p class="eyebrow eyebrow--brass">Dossier section</p>
							<h1 id="section-heading" class="mt-2 font-display text-[clamp(2rem,4vw,3.1rem)] font-normal leading-[1.02] tracking-[-0.02em] text-ink">{{ activeSection.label }}</h1>
							<p class="mt-3 max-w-[52ch] text-sm leading-7 text-muted">{{ activeSection.description }}</p>
						</header>
					</div>

					<div class="shell-max pb-16 pt-6">
						<NoticeBar v-if="alert" class="mb-5" :type="alert.type" :message="alert.message" @dismiss="alert = null" />

						<section v-if="activeTab === 'overview'" class="grid items-start gap-5 lg:grid-cols-[1.45fr_1fr]" aria-labelledby="overview-heading">
							<div class="sheet">
								<SheetHeader
									eyebrow="Workspace index"
									title="Everything for your audit, in one place."
									title-id="overview-heading"
									description="Keep your organization records current, share compliance evidence, and handle day-to-day audit work from one workspace."
								/>
								<div class="grid grid-cols-1 min-[720px]:grid-cols-2">
									<button v-for="entry in workspaceIndex" :key="entry.title" class="group grid cursor-pointer grid-cols-[1fr_auto] gap-x-4 gap-y-1 border-b border-line bg-transparent px-[1.4rem] py-[1.1rem] text-left transition odd:border-r hover:border-brass/60 hover:bg-canvas-soft max-[720px]:border-r-0 last:odd:border-r-0" @click="openTab(entry.tab)">
										<span class="col-span-full flex items-center gap-2">
											<svg viewBox="0 0 24 24" class="size-3.5 text-muted" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
												<path v-for="path in entry.icon" :d="path" />
											</svg>
											<span class="font-mono text-[0.5625rem] font-medium uppercase tracking-[0.16em] text-brass-strong">{{ entry.kicker }}</span>
										</span>
										<span class="mt-[0.3rem] text-[0.9375rem] font-semibold text-ink">{{ entry.title }}</span>
										<span class="mt-[0.15rem] text-[0.78rem] leading-normal text-muted">{{ entry.description }}</span>
										<span class="col-start-2 row-[2/span_2] flex flex-col items-end justify-center gap-3">
											<span class="status-stamp border-line bg-paper text-muted-strong">{{ tileStatus(entry) }}</span>
											<span class="text-base text-line-strong transition group-hover:translate-x-1 group-hover:text-bottle" aria-hidden="true">→</span>
										</span>
									</button>
								</div>
							</div>

							<aside class="sheet" aria-label="Your dossier">
								<div class="sheet-body">
									<p class="eyebrow eyebrow--brass">Your dossier</p>
									<h2 class="sheet-title mt-2">One organization, one record.</h2>
									<p class="sheet-sub">Update organization details, record financial information, manage tax registrations, and share requested documents securely.</p>
									<KeyValueList :items="dossierDetails" />
									<Button class="audit-btn audit-btn--secondary mt-5 w-full justify-center" @click="openTab('organization')">Open organization records</Button>
								</div>
							</aside>
						</section>

						<section v-else-if="activeTab === 'quotations'" class="sheet" aria-labelledby="quotations-heading">
							<SheetHeader
								eyebrow="Commercial"
								title="Proposals"
								title-id="quotations-heading"
								description="Open a proposal to see the amount and choose whether to accept or decline."
							>
								<template #actions>
									<Button class="audit-btn audit-btn--secondary audit-btn--sm" :disabled="refreshing" @click="loadPortal()">
										{{ refreshing ? "Updating…" : "Refresh" }}
									</Button>
								</template>
							</SheetHeader>
							<ResponsiveLedger
								:columns="quotationColumns"
								:items="portal.quotations"
								empty-title="No proposals to review"
								empty-description="Your audit team will share a proposal here when it’s ready."
							>
								<template #cell-name="{ item }"><span class="cell-ref">{{ item.name }}</span></template>
								<template #cell-transaction_date="{ item }">{{ formatDate(item.transaction_date) }}</template>
								<template #cell-valid_till="{ item }">{{ formatDate(item.valid_till) }}</template>
								<template #cell-grand_total="{ item }">{{ formatCurrency(item.grand_total, item.currency) }}</template>
								<template #cell-status="{ item }"><StatusPill :status="item.status" /></template>
								<template #cell-choice="{ item }">
									<Button v-if="item.status === 'Open'" class="audit-btn audit-btn--secondary audit-btn--sm" @click="openQuotation(item)">Review proposal</Button>
									<button v-else class="text-action" @click="openQuotation(item)">View proposal</button>
								</template>
								<template #mobile="{ item }">
									<div class="flex items-start justify-between gap-3">
										<div>
											<h3 class="record-title">Proposal {{ item.name }}</h3>
											<p class="record-note">Reply by {{ formatDate(item.valid_till) }}</p>
										</div>
										<StatusPill :status="item.status" />
									</div>
									<p class="figure mt-4 text-lg font-semibold text-slate-900">{{ formatCurrency(item.grand_total, item.currency) }}</p>
									<Button class="audit-btn audit-btn--secondary audit-btn--sm mt-4 w-full justify-center" @click="openQuotation(item)">View proposal</Button>
								</template>
							</ResponsiveLedger>
						</section>

						<section v-else-if="activeTab === 'invoices'" class="sheet" aria-labelledby="invoices-heading">
							<SheetHeader
								eyebrow="Billing"
								title="Invoices"
								title-id="invoices-heading"
								description="Select “View details” for the line items or download a copy for your records."
							>
								<template #actions>
									<Button class="audit-btn audit-btn--secondary audit-btn--sm" :disabled="refreshing" @click="loadPortal()">
										{{ refreshing ? "Updating…" : "Refresh" }}
									</Button>
								</template>
							</SheetHeader>
							<ResponsiveLedger
								:columns="invoiceColumns"
								:items="portal.invoices"
								min-width="min-w-[850px]"
								empty-title="No invoices yet"
								empty-description="Invoices from your audit team will appear here."
							>
								<template #cell-name="{ item }"><span class="cell-ref">{{ item.name }}</span></template>
								<template #cell-posting_date="{ item }">{{ formatDate(item.posting_date) }}</template>
								<template #cell-due_date="{ item }">{{ formatDate(item.due_date) }}</template>
								<template #cell-grand_total="{ item }">{{ formatCurrency(item.grand_total, item.currency) }}</template>
								<template #cell-outstanding_amount="{ item }">
									<span :class="item.outstanding_amount > 0 ? 'amount-due' : 'amount-clear'">{{ formatCurrency(item.outstanding_amount, item.currency) }}</span>
								</template>
								<template #cell-status="{ item }"><StatusPill :status="item.status" /></template>
								<template #cell-options="{ item }">
									<div class="flex justify-end gap-4">
										<button class="text-action" @click="openInvoice(item)">View details</button>
										<a class="text-action text-action--muted" :href="item.pdf_url" target="_blank" rel="noopener">Download copy</a>
									</div>
								</template>
								<template #mobile="{ item }">
									<div class="flex items-start justify-between gap-3">
										<div>
											<h3 class="record-title">Invoice {{ item.name }}</h3>
											<p class="record-note">Pay by {{ formatDate(item.due_date) }}</p>
										</div>
										<StatusPill :status="item.status" />
									</div>
									<KeyValueList
										class="mt-4"
										variant="grid"
										:items="[
											{ label: 'Total', value: formatCurrency(item.grand_total, item.currency) },
											{ label: 'Still to pay', value: formatCurrency(item.outstanding_amount, item.currency) },
										]"
									>
										<template #value="{ item: detail }">
											<span class="figure mt-1 font-semibold text-slate-900" :class="detail.label === 'Still to pay' && item.outstanding_amount > 0 ? 'amount-due' : ''">{{ detail.value }}</span>
										</template>
									</KeyValueList>
									<div class="mt-4 flex flex-wrap gap-4">
										<button class="text-action" @click="openInvoice(item)">View details</button>
										<a class="text-action text-action--muted" :href="item.pdf_url" target="_blank" rel="noopener">Download copy</a>
									</div>
								</template>
							</ResponsiveLedger>
						</section>

						<Suspense v-if="isDossierTab">
							<ClientRecordsWorkspace :area="activeTab" :section="activeSubTab" @update:section="openOrganizationSection" />
							<template #fallback>
								<StatePanel label="Opening records" title="Opening records…" message="Loading your organization’s private records." />
							</template>
						</Suspense>

						<p class="mt-5 text-[0.6875rem] leading-relaxed text-muted">Your records are private and visible only to your organization and audit team.</p>
					</div>
				</template>
			</main>

			<DialogFrame v-model:open="invoiceDialogOpen" size="3xl" description="Review the line items and payment status for this invoice.">
				<template #title>
					<div>
						<p class="eyebrow">Invoice</p>
						<h2 class="mt-0.5 font-display text-[1.6rem] font-normal leading-[1.1] tracking-[-0.01em] text-ink">{{ invoiceDetails?.name || "Invoice details" }}</h2>
					</div>
				</template>
				<StatePanel v-if="invoiceLoading" tone="loading" :sheet="false" dense label="Loading invoice details" message="Loading invoice details…" />
				<NoticeBar v-else-if="invoiceError" type="error" :message="invoiceError" :dismissible="false" />
				<template v-else-if="invoiceDetails">
					<KeyValueList
						variant="grid"
						:items="[
							{ label: 'Payment status', value: invoiceDetails.status },
							{ label: 'Invoice date', value: formatDate(invoiceDetails.posting_date) },
							{ label: 'Pay by', value: formatDate(invoiceDetails.due_date) },
						]"
					>
						<template #value="{ item }">
							<StatusPill v-if="item.label === 'Payment status'" :status="invoiceDetails.status" />
							<span v-else class="mt-1.5 text-sm text-ink">{{ item.value }}</span>
						</template>
					</KeyValueList>
					<div class="overflow-hidden rounded-[0.65rem] border border-line">
						<div class="overflow-x-auto">
							<table class="ledger w-full min-w-[520px]">
								<thead>
									<tr>
										<th>Item</th>
										<th class="text-right">Qty</th>
										<th class="text-right">Rate</th>
										<th class="text-right">Amount</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="(item, index) in invoiceDetails.items" :key="`${item.item_code}-${index}`">
										<td>
											<span class="cell-strong">{{ item.item_name || item.item_code }}</span>
											<span v-if="item.description" class="record-note block">{{ item.description }}</span>
										</td>
										<td class="cell-num text-right">{{ item.qty }}</td>
										<td class="cell-num text-right">{{ formatCurrency(item.rate, invoiceDetails.currency) }}</td>
										<td class="cell-num cell-strong text-right">{{ formatCurrency(item.amount, invoiceDetails.currency) }}</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>
					<KeyValueList
						variant="plain"
						class="ml-auto mt-5 w-full max-w-xs border-t border-line pt-4"
						:items="[
							{ label: 'Total', value: formatCurrency(invoiceDetails.grand_total, invoiceDetails.currency) },
							{ label: 'Still to pay', value: formatCurrency(invoiceDetails.outstanding_amount, invoiceDetails.currency) },
						]"
					>
						<template #value="{ item }">
							<span :class="item.label === 'Still to pay' ? 'amount-due' : ''">{{ item.value }}</span>
						</template>
					</KeyValueList>
				</template>
				<template #actions="{ close }">
					<Button class="audit-btn audit-btn--secondary" @click="close">Close</Button>
					<a v-if="invoiceUrl" :href="invoiceUrl" target="_blank" rel="noopener" class="audit-btn audit-btn--primary">Download PDF</a>
				</template>
			</DialogFrame>

			<DialogFrame v-model:open="quotationDetailsDialogOpen" size="3xl" description="Review the included work, total, and terms before responding.">
				<template #title>
					<div>
						<p class="eyebrow">Proposal</p>
						<h2 class="mt-0.5 font-display text-[1.6rem] font-normal leading-[1.1] tracking-[-0.01em] text-ink">{{ quotationDetails?.name || selectedQuotation?.name || "Proposal details" }}</h2>
					</div>
				</template>
				<StatePanel v-if="quotationDetailsLoading" tone="loading" :sheet="false" dense label="Opening proposal details" message="Opening proposal details…" />
				<NoticeBar v-else-if="quotationDetailsError" type="error" :message="quotationDetailsError" :dismissible="false" />
				<template v-else-if="quotationDetails">
					<KeyValueList
						variant="grid"
						:items="[
							{ label: 'Total', value: formatCurrency(quotationDetails.grand_total, quotationDetails.currency) },
							{ label: 'Received', value: formatDate(quotationDetails.transaction_date) },
							{ label: 'Please reply by', value: formatDate(quotationDetails.valid_till) },
						]"
					>
						<template #value="{ item }">
							<span :class="item.label === 'Total' ? 'mt-1.5 font-display text-[1.9rem] font-normal leading-none text-ink' : 'mt-1.5 text-sm text-ink'">{{ item.value }}</span>
						</template>
					</KeyValueList>
					<div class="overflow-hidden rounded-[0.65rem] border border-line">
						<div class="overflow-x-auto">
							<table class="ledger w-full min-w-[520px]">
								<thead>
									<tr>
										<th>Included work</th>
										<th class="text-right">Quantity</th>
										<th class="text-right">Rate</th>
										<th class="text-right">Amount</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="(item, index) in quotationDetails.items" :key="`${item.item_code}-${index}`">
										<td>
											<span class="cell-strong">{{ item.item_name || item.item_code }}</span>
											<span v-if="item.description" class="record-note block">{{ item.description }}</span>
										</td>
										<td class="cell-num text-right">{{ item.qty }} {{ item.uom || "" }}</td>
										<td class="cell-num text-right">{{ formatCurrency(item.rate, quotationDetails.currency) }}</td>
										<td class="cell-num cell-strong text-right">{{ formatCurrency(item.amount, quotationDetails.currency) }}</td>
									</tr>
									<tr v-if="quotationDetails.items.length === 0">
										<td colspan="4" class="py-8 text-center text-slate-500">No line items were included.</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>
					<div v-if="quotationDetails.terms">
						<p class="eyebrow">Notes and terms</p>
						<p class="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">{{ quotationDetails.terms }}</p>
					</div>
					<NoticeBar type="info" :dismissible="false">Accepting or declining records your choice for your audit team. It does not collect a payment.</NoticeBar>
				</template>
				<template #actions="{ close }">
					<Button class="audit-btn audit-btn--secondary" @click="close">Close</Button>
					<template v-if="quotationDetails?.status === 'Open'">
						<Button class="audit-btn audit-btn--danger" @click="requestQuotationDecision(selectedQuotation, 'reject')">Decline proposal</Button>
						<Button class="audit-btn audit-btn--primary" @click="requestQuotationDecision(selectedQuotation, 'accept')">Accept proposal</Button>
					</template>
				</template>
			</DialogFrame>

			<DialogFrame v-model:open="quotationDialogOpen" size="md" description="Confirm your response to this proposal.">
				<template #title>
					<div>
						<p class="eyebrow">Confirm your decision</p>
						<h2 class="mt-0.5 font-display text-[1.6rem] font-normal leading-[1.1] tracking-[-0.01em] text-ink">{{ quotationAction === "accept" ? "Accept this proposal?" : "Decline this proposal?" }}</h2>
					</div>
				</template>
				<div class="pb-2 text-sm leading-6 text-slate-600">
					<p v-if="selectedQuotation">
						You’re choosing to {{ quotationAction === "accept" ? "accept" : "decline" }}
						<strong class="font-semibold text-slate-900">{{ selectedQuotation.name }}</strong>
						for <strong class="font-semibold text-slate-900">{{ formatCurrency(selectedQuotation.grand_total, selectedQuotation.currency) }}</strong>.
					</p>
					<p class="mt-3">Your choice will be recorded on the proposal for your audit team. This action does not collect a payment.</p>
				</div>
				<template #actions="{ close }">
					<Button class="audit-btn audit-btn--secondary" :disabled="Boolean(activeQuotation)" @click="close">Go back</Button>
					<Button
						:class="quotationAction === 'accept' ? 'audit-btn audit-btn--primary' : 'audit-btn audit-btn--danger'"
						:disabled="Boolean(activeQuotation)"
						@click="confirmQuotationDecision"
					>
						{{ activeQuotation ? "Saving your choice…" : quotationAction === "accept" ? "Yes, accept proposal" : "Yes, decline proposal" }}
					</Button>
				</template>
			</DialogFrame>
		</div>
	</FrappeUIProvider>
</template>
