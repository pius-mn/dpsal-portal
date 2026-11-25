<script setup>
import { computed, onMounted, ref } from "vue"
import { Button } from "frappe-ui"
import KeyValueList from "../components/KeyValueList.vue"
import NoticeBar from "../components/NoticeBar.vue"
import RecordCollection from "../components/RecordCollection.vue"
import RecordEditorDialog from "../components/RecordEditorDialog.vue"
import SheetHeader from "../components/SheetHeader.vue"
import StatePanel from "../components/StatePanel.vue"
import StatusPill from "../components/StatusPill.vue"
import { display, formatDate } from "../lib/format"
import {
	appointmentFields,
	auditRecordTypes,
	buildRecordDefinitions,
	credentialFields,
	customerFields,
} from "../lib/records"
import { createPortalResource, createUploadResource, fetchResource } from "../lib/resources"
import { organizationSections } from "../lib/workspace"

const props = defineProps({
	area: { type: String, required: true },
	section: { type: String, default: "details" },
})
const emit = defineEmits(["update:section"])

const recordsResource = createPortalResource("audit_portal.api.client_records.get_client_records")
const customerSaveResource = createPortalResource("audit_portal.api.client_records.save_customer_details", { method: "POST" })
const appointmentBookResource = createPortalResource("audit_portal.api.client_records.book_client_appointment", { method: "POST" })
const linkedRecordResource = createPortalResource("audit_portal.api.client_records.save_customer_linked_record", { method: "POST" })
const clientRecordResource = createPortalResource("audit_portal.api.client_records.save_client_record", { method: "POST" })
const appointmentCancelResource = createPortalResource("audit_portal.api.client_records.cancel_client_appointment", { method: "POST" })
const uploadResource = createUploadResource("audit_portal.api.client_records.upload_compliance_file")
const credentialListResource = createPortalResource("audit_portal.api.credentials.get_client_credentials")
const credentialSubmitResource = createPortalResource("audit_portal.api.credentials.submit_client_credential", { method: "POST" })

const workspace = computed(() => recordsResource.data)
const loading = computed(() =>
	recordsResource.loading ||
	(props.area === "credentials" && credentialListResource.loading) ||
	(!recordsResource.fetched && !recordsResource.error),
)
const saving = computed(() =>
	customerSaveResource.loading ||
	appointmentBookResource.loading ||
	linkedRecordResource.loading ||
	clientRecordResource.loading ||
	uploadResource.loading ||
	credentialSubmitResource.loading,
)
const pageError = ref("")
const notice = ref("")
const editorOpen = ref(false)
const editorError = ref("")
const editorKind = ref("")
const selectedRecord = ref(null)
const activeSectionId = computed(() => organizationSections.some((item) => item.id === props.section) ? props.section : "details")
const activeGovernance = computed(() => organizationSections.find((item) => item.id === activeSectionId.value)?.doctype || "Organization Details")
const uploadingDocument = ref(null)
const credentialRequests = ref([])

const recordDefinitions = computed(() => buildRecordDefinitions(workspace.value))
const profileFields = computed(() => customerFields(workspace.value))
const currentDefinition = computed(() => recordDefinitions.value[editorKind.value] || null)
const editorFields = computed(() => {
	if (editorKind.value === "Organization Details") return profileFields.value
	if (editorKind.value === "Appointment") return appointmentFields
	if (editorKind.value === "Credential") return credentialFields
	return currentDefinition.value?.fields || []
})
const editorTitle = computed(() => {
	if (editorKind.value === "Organization Details") return "Update your organization details"
	if (editorKind.value === "Appointment") return "Book an appointment"
	if (editorKind.value === "Credential") return selectedRecord.value ? "Submit a replacement credential" : "Submit a credential for review"
	return `${selectedRecord.value ? "Update" : "Add"} ${currentDefinition.value?.title?.replace(/s$/, "").toLowerCase() || "record"}`
})
const editorDescription = computed(() => {
	if (editorKind.value === "Appointment") return "Choose a future date and time. Your audit team will confirm the meeting."
	if (editorKind.value === "Credential") return "Your audit team reviews this request in Desk. The password is stored securely and is never shown here after submission."
	return "Enter the information your audit team needs. You can return and update it later."
})
const editorSaveLabel = computed(() => {
	if (editorKind.value === "Credential") return "Submit for review"
	if (editorKind.value === "Appointment") return "Book appointment"
	return selectedRecord.value || editorKind.value === "Organization Details"
		? "Save changes"
		: "Add record"
})

function recordDate(value) {
	return formatDate(value, "Not provided")
}

async function load() {
	pageError.value = ""
	try {
		await fetchResource(recordsResource, null, "We couldn’t load your organization records.")
		if (props.area === "credentials") {
			credentialRequests.value = await fetchResource(credentialListResource, null, "We couldn’t load your credential requests.")
		}
	} catch (error) {
		pageError.value = error.message
	}
}

function openEditor(kind, record = null) {
	editorKind.value = kind
	selectedRecord.value = record
	editorError.value = ""
	editorOpen.value = true
}

async function saveRecord({ name, values }) {
	editorError.value = ""
	try {
		if (editorKind.value === "Credential") {
			const result = await fetchResource(credentialSubmitResource, values, "We couldn’t submit these credentials.")
			notice.value = result.message
			editorOpen.value = false
			await load()
			return
		}
		if (editorKind.value === "Organization Details") {
			await fetchResource(customerSaveResource, { values }, "We couldn’t save these changes.")
		} else if (editorKind.value === "Appointment") {
			await fetchResource(appointmentBookResource, {
				date: values.date,
				time: values.time,
				purpose: values.purpose,
				notes: values.notes,
			}, "We couldn’t book this appointment.")
		} else if (editorKind.value === "Contact" || editorKind.value === "Address") {
			await fetchResource(linkedRecordResource, { doctype: editorKind.value, name, values }, "We couldn’t save these changes.")
		} else {
			const cleanValues = { ...values }
			const file = cleanValues.file
			delete cleanValues.file
			const result = await fetchResource(clientRecordResource, {
				doctype: editorKind.value,
				name,
				values: cleanValues,
			}, "We couldn’t save these changes.")
			selectedRecord.value = { ...cleanValues, name: result.name }
			if (file instanceof File) {
				await fetchResource(uploadResource, {
					args: { certificate_name: result.name },
					file,
				}, "We couldn’t upload this document.")
			}
		}
		editorOpen.value = false
		notice.value = "Your changes have been saved."
		await load()
	} catch (error) {
		editorError.value = error.message
	}
}

async function cancelAppointment(appointment) {
	pageError.value = ""
	try {
		const result = await fetchResource(appointmentCancelResource, { name: appointment.name }, "We couldn’t cancel the appointment.")
		notice.value = result.message
		await load()
	} catch (error) {
		pageError.value = error.message
	}
}

async function uploadDocument(item, event) {
	const file = event.target.files?.[0]
	if (!file) return

	pageError.value = ""
	uploadingDocument.value = item.name
	try {
		const result = await fetchResource(uploadResource, {
			args: { certificate_name: item.name },
			file,
		}, "We couldn’t upload this document.")
		notice.value = result.message
		await load()
	} catch (error) {
		pageError.value = error.message
	} finally {
		uploadingDocument.value = null
		event.target.value = ""
	}
}

onMounted(load)
</script>

<template>
	<div class="space-y-5">
		<StatePanel
			v-if="pageError && !workspace"
			tone="error"
			eyebrow="Records unavailable"
			title="Your records couldn’t be loaded"
			:message="pageError"
		>
			<template #actions>
				<Button class="audit-btn audit-btn--secondary" @click="load">Try again</Button>
			</template>
		</StatePanel>
		<div v-else class="space-y-5">
			<NoticeBar v-if="pageError" type="error" :message="pageError" @dismiss="pageError = ''" />
			<NoticeBar v-if="notice" type="success" :message="notice" @dismiss="notice = ''" />

			<div v-if="props.area === 'organization'" class="grid gap-5 lg:grid-cols-[13rem_minmax(0,1fr)] lg:gap-6">
				<aside class="min-w-0">
					<p class="eyebrow px-3 pb-2">Dossier</p>
					<nav class="no-scrollbar flex gap-1.5 overflow-x-auto border-b border-line pb-2 lg:sticky lg:top-[5.5rem] lg:flex-col lg:border-b-0 lg:pb-0" aria-label="Organization sections">
						<button
							v-for="section in organizationSections"
							:key="section.id"
							type="button"
							class="flex flex-none items-center gap-2 whitespace-nowrap rounded-[0.55rem] border px-3 py-2 text-left text-[0.78rem] font-medium transition lg:w-full"
							:class="activeSectionId === section.id ? 'border-brass/40 bg-bottle-soft/80 text-bottle-deep' : 'border-transparent text-muted hover:border-line hover:bg-canvas-soft hover:text-ink'"
							:aria-current="activeSectionId === section.id ? 'page' : undefined"
							@click="emit('update:section', section.id)"
						>
							<span class="h-3.5 w-[2px] shrink-0 rounded-full" :class="activeSectionId === section.id ? 'bg-brass' : 'bg-transparent'" aria-hidden="true"></span>
							<span>{{ section.label }}</span>
						</button>
					</nav>
				</aside>

				<div class="min-w-0 space-y-5">
				<div v-if="activeSectionId === 'contacts'" class="space-y-5">
					<RecordCollection
						eyebrow="Directory"
						title="Organization contacts"
						description="Keep the people your audit team should contact up to date."
						:items="workspace?.contacts || []"
						empty-title="No contacts added"
						empty-description="Add a contact person for questions about your organization."
						add-label="Add a contact"
						:loading="loading"
						@add="openEditor('Contact')"
					>
						<template #summary="{ item }">
							<h3 class="record-title">{{ [item.first_name, item.last_name].filter(Boolean).join(" ") }}</h3>
							<p class="record-meta">{{ [item.designation, item.department].filter(Boolean).join(" · ") || "Contact person" }}</p>
							<p class="record-note">{{ [item.email, item.phone].filter(Boolean).join(" · ") || "No contact details provided" }}</p>
						</template>
						<template #actions="{ item }">
							<Button v-if="item.can_edit" class="audit-btn audit-btn--secondary audit-btn--sm" @click="openEditor('Contact', item)">Edit</Button>
							<span v-else class="record-note">Ask your audit team to update this shared contact</span>
						</template>
					</RecordCollection>

					<RecordCollection
						eyebrow="Directory"
						title="Organization addresses"
						description="Add addresses for your organization and choose which one to use by default on new quotations and invoices."
						:items="workspace?.addresses || []"
						empty-title="No addresses added"
						empty-description="Add an address so your audit team can keep the organization record complete."
						add-label="Add an address"
						:loading="loading"
						@add="openEditor('Address')"
					>
						<template #summary="{ item }">
							<h3 class="record-title">{{ item.address_title || item.address_type }}</h3>
							<p v-if="item.is_primary_address" class="record-flag">Default billing address for new quotations and invoices</p>
							<p class="record-meta">{{ item.address_line1 }}<span v-if="item.address_line2">, {{ item.address_line2 }}</span></p>
							<p class="record-note">{{ [item.city, item.state, item.pincode, item.country].filter(Boolean).join(", ") }}</p>
						</template>
						<template #actions="{ item }">
							<Button v-if="item.can_edit" class="audit-btn audit-btn--secondary audit-btn--sm" @click="openEditor('Address', item)">Edit</Button>
							<span v-else class="record-note">Ask your audit team to update this shared address</span>
						</template>
					</RecordCollection>
				</div>

				<section v-if="activeSectionId === 'details'" class="sheet">
					<SheetHeader
						eyebrow="Organization profile"
						title="Organization details"
						description="Keep your registration and legal details current for your audit team."
					>
						<template #actions>
							<Button class="audit-btn audit-btn--primary" :disabled="loading" @click="openEditor('Organization Details', workspace?.customer_details)">Edit organization details</Button>
						</template>
					</SheetHeader>
					<StatePanel v-if="loading" tone="loading" :sheet="false" dense message="Loading your information…" />
					<KeyValueList
						v-else
						variant="grid"
						:items="profileFields.map((field) => ({
							label: field.label,
							value: field.type === 'date' ? recordDate(workspace?.customer_details?.[field.name]) : display(workspace?.customer_details?.[field.name]),
							muted: !workspace?.customer_details?.[field.name],
						}))"
					>
						<template #value="{ item }">
							<span :class="item.muted ? 'italic text-muted' : 'text-ink'">{{ item.value }}</span>
						</template>
					</KeyValueList>
				</section>

				<RecordCollection
					v-else-if="activeSectionId !== 'details' && activeSectionId !== 'contacts'"
					eyebrow="Governance"
					:title="recordDefinitions[activeGovernance].title"
					description="These details are visible only to your organization and its audit team."
					:items="workspace?.records?.[activeGovernance] || []"
					:empty-title="recordDefinitions[activeGovernance].emptyTitle"
					:empty-description="recordDefinitions[activeGovernance].emptyDescription"
					:add-label="`Add ${recordDefinitions[activeGovernance].title.toLowerCase().replace(/s$/, '')}`"
					:loading="loading"
					@add="openEditor(activeGovernance)"
				>
					<template #summary="{ item }">
						<h3 class="record-title">{{ item[recordDefinitions[activeGovernance].titleField] }}</h3>
						<p class="record-meta">
							<template v-if="activeGovernance === 'Client Shareholder'">{{ display(item.share_pct) }}% ownership · {{ display(item.person_nature) }}</template>
							<template v-else-if="activeGovernance === 'Client Beneficial Owner'">{{ display(item.ownership_pct) }}% ownership · {{ display(item.ownership_form) }}</template>
							<template v-else>{{ display(item.designation_internal || item.role) }} · {{ display(item.email) }}</template>
						</p>
					</template>
					<template #actions="{ item }">
						<Button class="audit-btn audit-btn--secondary audit-btn--sm" @click="openEditor(activeGovernance, item)">Edit</Button>
					</template>
				</RecordCollection>
				</div>
			</div>

			<RecordCollection
				v-else-if="props.area === 'tax'"
				eyebrow="Compliance"
				:title="recordDefinitions['Client Tax Registration'].title"
				description="Track filing frequency, due dates, and the latest declared and paid periods."
				:items="workspace?.records?.['Client Tax Registration'] || []"
				:empty-title="recordDefinitions['Client Tax Registration'].emptyTitle"
				:empty-description="recordDefinitions['Client Tax Registration'].emptyDescription"
				add-label="Add tax registration"
				:loading="loading"
				@add="openEditor('Client Tax Registration')"
			>
				<template #summary="{ item }">
					<h3 class="record-title">{{ item.tax_type }}</h3>
					<p class="record-meta">{{ display(item.frequency) }} filing · next due {{ recordDate(item.due_date) }}</p>
					<p class="record-note">Last declared {{ recordDate(item.declared_date) }} · last paid {{ recordDate(item.payment_date) }}</p>
				</template>
				<template #actions="{ item }">
					<Button class="audit-btn audit-btn--secondary audit-btn--sm" @click="openEditor('Client Tax Registration', item)">Edit</Button>
				</template>
			</RecordCollection>

			<div v-else-if="props.area === 'audit_data'" class="space-y-5">
				<RecordCollection
					v-for="doctype in auditRecordTypes"
					:key="doctype"
					eyebrow="Finance"
					:title="recordDefinitions[doctype].title"
					:description="recordDefinitions[doctype].emptyDescription"
					:items="workspace?.records?.[doctype] || []"
					:empty-title="recordDefinitions[doctype].emptyTitle"
					:empty-description="recordDefinitions[doctype].emptyDescription"
					:add-label="`Add ${recordDefinitions[doctype].title.replace(/^Client /, '').replace(/s$/, '').toLowerCase()}`"
					:loading="loading"
					@add="openEditor(doctype)"
				>
					<template #summary="{ item }">
						<h3 class="record-title">{{ item[recordDefinitions[doctype].titleField] }}</h3>
						<p v-if="doctype === 'Client Bank Account'" class="record-meta">
							{{ item.account_type || "Account" }} · {{ item.branch_name || "Branch not provided" }} · {{ item.currency || "Currency not provided" }}
						</p>
						<p v-else-if="doctype === 'Client Budget Line'" class="record-meta">
							{{ item.budget_period || "Period not provided" }} · budget {{ display(item.annual_budget || item.monthly_budget) }} {{ item.currency || "" }} · spent {{ display(item.actual_spend) }}
						</p>
					</template>
					<template #actions="{ item }">
						<Button class="audit-btn audit-btn--secondary audit-btn--sm" @click="openEditor(doctype, item)">Edit</Button>
					</template>
				</RecordCollection>
			</div>

			<RecordCollection
				v-else-if="props.area === 'documents'"
				eyebrow="Evidence"
				:title="recordDefinitions['Compliance Certificate'].title"
				description="Your audit team lists the documents they need here. Upload a PDF or image for each request."
				:items="workspace?.records?.['Compliance Certificate'] || []"
				:empty-title="recordDefinitions['Compliance Certificate'].emptyTitle"
				:empty-description="recordDefinitions['Compliance Certificate'].emptyDescription"
				add-label=""
				:loading="loading"
				hide-add
			>
				<template #summary="{ item }">
					<div class="flex flex-wrap items-center gap-2">
						<h3 class="record-title">{{ item.document_title }}</h3>
						<StatusPill :status="item.status" />
					</div>
					<p class="record-meta">{{ display(item.doc_type) }}<span v-if="item.has_expiry"> · expires {{ recordDate(item.expiry_date) }}</span></p>
					<p v-if="item.rejection_reason" class="record-danger">{{ item.rejection_reason }}</p>
					<a v-if="item.download_url" class="text-action mt-2 inline-flex" :href="item.download_url">Open uploaded file</a>
				</template>
				<template #actions="{ item }">
					<label class="audit-btn audit-btn--secondary audit-btn--sm inline-flex cursor-pointer" :class="{ 'pointer-events-none opacity-50': uploadingDocument === item.name }">
						{{ uploadingDocument === item.name ? "Uploading…" : item.attachment ? "Replace upload" : "Upload document" }}
						<input class="sr-only" type="file" accept=".pdf,.png,.jpg,.jpeg" :disabled="uploadingDocument === item.name" @change="uploadDocument(item, $event)">
					</label>
				</template>
			</RecordCollection>

			<RecordCollection
				v-else-if="props.area === 'credentials'"
				eyebrow="Access"
				title="External portal credentials"
				description="Share external portal logins for secure review. Do not include one-time codes or security answers."
				:items="credentialRequests"
				empty-title="No credentials submitted"
				empty-description="Submit a portal login when your audit team asks for access to an external system."
				add-label="Submit a credential"
				:loading="loading"
				@add="openEditor('Credential')"
			>
				<template #summary="{ item }">
					<div class="flex flex-wrap items-center gap-2">
						<h3 class="record-title">{{ item.portal_name }}</h3>
						<StatusPill :status="item.status" />
					</div>
					<p class="record-meta">{{ item.credential_type }} · {{ item.username }}</p>
					<p class="record-note">Submitted {{ recordDate(item.submitted_on) }}<span v-if="item.reviewed_on"> · reviewed {{ recordDate(item.reviewed_on) }}</span></p>
					<p v-if="item.reviewer_note" class="record-danger">{{ item.reviewer_note }}</p>
				</template>
				<template #actions="{ item }">
					<Button
						v-if="item.status !== 'Pending Review'"
						class="audit-btn audit-btn--secondary audit-btn--sm"
						@click="openEditor('Credential', item)"
					>
						Submit replacement
					</Button>
					<span v-else class="record-note">Awaiting review</span>
				</template>
			</RecordCollection>

			<template v-else-if="props.area === 'appointments'">
				<RecordCollection
					eyebrow="Meetings"
					title="Appointments"
					description="Book a time with your audit team or cancel a future appointment."
					:items="workspace?.appointments || []"
					empty-title="No appointments yet"
					empty-description="Book a meeting when you need to discuss your account or upcoming work."
					add-label="Book an appointment"
					:loading="loading"
					@add="openEditor('Appointment')"
				>
					<template #summary="{ item }">
						<div class="flex flex-wrap items-center gap-2">
							<h3 class="record-title">{{ item.purpose || "Meeting with your audit team" }}</h3>
							<StatusPill :status="item.status" />
						</div>
						<p class="record-meta">{{ recordDate(item.scheduled_time) }} · {{ item.scheduled_time?.split(" ")[1]?.slice(0, 5) || "" }}</p>
						<p v-if="item.notes" class="record-note">{{ item.notes }}</p>
					</template>
					<template #actions="{ item }">
						<Button v-if="item.status !== 'Closed'" class="audit-btn audit-btn--danger audit-btn--sm" @click="cancelAppointment(item)">Cancel appointment</Button>
					</template>
				</RecordCollection>
			</template>

			<RecordEditorDialog
				v-model:open="editorOpen"
				:title="editorTitle"
				:description="editorDescription"
				:fields="editorFields"
				:record="selectedRecord"
				:saving="saving"
				:error="editorError"
				:save-label="editorSaveLabel"
				@save="saveRecord"
			/>
		</div>
	</div>
</template>
