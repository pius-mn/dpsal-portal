<script setup>
import { computed, reactive, ref } from "vue"
import { Button, FrappeUIProvider } from "frappe-ui"
import FormField from "../components/FormField.vue"
import NoticeBar from "../components/NoticeBar.vue"
import PortalHeader from "../components/PortalHeader.vue"
import SheetHeader from "../components/SheetHeader.vue"
import { signupFields } from "../lib/records"
import { createPortalResource, fetchResource } from "../lib/resources"

const user = document.querySelector("#app")?.dataset.user || "Guest"
const isLoggedIn = computed(() => user !== "Guest")
const submitted = ref(null)
const errorMessage = ref("")
const emptyForm = {
	company_name: "",
	contact_name: "",
	email: "",
	phone: "",
	notes: "",
}
const form = reactive({ ...emptyForm })
const signupRequest = createPortalResource("audit_portal.api.signup.submit_signup_request", { method: "POST" })

async function submitRequest() {
	errorMessage.value = ""
	submitted.value = null
	const args = Object.fromEntries(
		Object.entries(form).map(([key, value]) => [key, String(value || "").trim()]),
	)
	try {
		submitted.value = await fetchResource(signupRequest, args, "We couldn’t submit your request. Please try again.")
		Object.assign(form, emptyForm)
	} catch (error) {
		errorMessage.value = error.message
	}
}
</script>

<template>
	<FrappeUIProvider>
		<div class="min-h-screen font-sans text-ink">
			<PortalHeader :user="user" context="signup" />

			<main class="shell-max grid grid-cols-1 items-start gap-10 py-[clamp(1.75rem,5vw,4rem)] min-[960px]:grid-cols-[minmax(0,1.05fr)_minmax(22rem,0.8fr)]">
				<section class="dossier-cover p-[clamp(1.75rem,4vw,3.25rem)]" aria-labelledby="signup-heading">
					<p class="eyebrow eyebrow--light">A clear start to the engagement</p>
					<h1 id="signup-heading" class="mt-4 max-w-[12ch] text-balance font-display text-[clamp(2.8rem,7vw,5rem)] font-normal leading-[0.95] tracking-[-0.02em] text-[#f8fbf9]">Bring your audit into focus.</h1>
					<p class="mt-5 max-w-[34rem] text-[1.05rem] leading-[1.7] text-[#e9f2ed]/75">Request a private workspace for your organization. Our team reviews each request before creating portal access.</p>

					<ol class="mt-8 list-none border-t border-white/15 p-0">
						<li class="grid grid-cols-[2.25rem_1fr] gap-4 border-b border-white/15 py-[1.1rem]">
							<span class="pt-0.5 font-mono text-[0.6875rem] text-brass">01</span>
							<div>
								<p class="m-0 text-sm font-semibold text-[#f2f8f5]">Send your organization details</p>
								<p class="mt-1 text-[0.8125rem] leading-[1.55] text-[#e9f2ed]/60">Tell us who to contact and what your team needs.</p>
							</div>
						</li>
						<li class="grid grid-cols-[2.25rem_1fr] gap-4 border-b border-white/15 py-[1.1rem]">
							<span class="pt-0.5 font-mono text-[0.6875rem] text-brass">02</span>
							<div>
								<p class="m-0 text-sm font-semibold text-[#f2f8f5]">Our team reviews the request</p>
								<p class="mt-1 text-[0.8125rem] leading-[1.55] text-[#e9f2ed]/60">We confirm the organization and prepare the right access.</p>
							</div>
						</li>
						<li class="grid grid-cols-[2.25rem_1fr] gap-4 border-b border-white/15 py-[1.1rem]">
							<span class="pt-0.5 font-mono text-[0.6875rem] text-brass">03</span>
							<div>
								<p class="m-0 text-sm font-semibold text-[#f2f8f5]">Your private workspace opens</p>
								<p class="mt-1 text-[0.8125rem] leading-[1.55] text-[#e9f2ed]/60">We contact the business email once access is approved.</p>
							</div>
						</li>
					</ol>
				</section>

				<section class="sheet" aria-labelledby="signup-title">
					<SheetHeader
						eyebrow="Access request"
						title="Organization details"
						title-id="signup-title"
						description="Fields marked * are required."
					/>

					<div class="sheet-body space-y-5">
						<NoticeBar v-if="isLoggedIn" type="info" :dismissible="false">
							You’re signed in as <strong>{{ user }}</strong>. If you already have client access, go to your <a href="/client-portal" class="font-semibold underline">client workspace</a>.
						</NoticeBar>

						<NoticeBar v-if="errorMessage" type="error" :message="errorMessage" @dismiss="errorMessage = ''" />

						<div v-if="submitted" class="receipt" role="status">
							<p class="eyebrow eyebrow--brass">Request received</p>
							<p class="mt-2 text-lg font-semibold text-slate-900">Thank you — your request is in review.</p>
							<p class="mt-2 text-sm leading-6 text-slate-600">{{ submitted.message }}</p>
							<p class="mt-4 flex flex-wrap items-baseline gap-2 border-t border-line pt-4 font-mono text-[0.6875rem] uppercase tracking-[0.08em] text-muted">Reference <strong class="text-[0.8125rem] tracking-[0.02em] text-ink">{{ submitted.name }}</strong></p>
							<button class="text-action mt-4" @click="submitted = null">Submit another request</button>
						</div>

						<form v-else class="space-y-4" @submit.prevent="submitRequest">
							<FormField
								v-for="field in signupFields"
								:key="field.name"
								:field="field"
								:model-value="form[field.name]"
								@update:model-value="form[field.name] = $event"
							/>
							<Button class="audit-btn audit-btn--primary w-full justify-center" type="submit" :disabled="signupRequest.loading">
								{{ signupRequest.loading ? "Sending request…" : "Request portal access" }}
							</Button>
							<p class="m-0 text-center text-[0.6875rem] leading-relaxed text-muted">Submitting this form creates a review request only. It does not create an account or customer record.</p>
						</form>
					</div>
				</section>
			</main>
		</div>
	</FrappeUIProvider>
</template>
