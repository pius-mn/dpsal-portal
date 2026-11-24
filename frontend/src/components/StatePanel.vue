<script setup>
import { computed } from "vue"

const props = defineProps({
	tone: { type: String, default: "loading" },
	title: { type: String, default: "" },
	message: { type: String, default: "" },
	label: { type: String, default: "" },
	eyebrow: { type: String, default: "Needs attention" },
	sheet: { type: Boolean, default: true },
	dense: { type: Boolean, default: false },
})

const role = computed(() => (props.tone === "error" ? "alert" : "status"))
const live = computed(() => (props.tone === "error" ? "assertive" : "polite"))
</script>

<template>
	<div
		:class="[
			sheet ? 'sheet mx-auto max-w-2xl' : '',
			dense ? 'px-6 py-10 text-center' : 'flex min-h-[18rem] flex-col items-center justify-center gap-3.5 p-8 text-center',
		]"
		:role="role"
		:aria-label="label || undefined"
	>
		<div :aria-live="live" aria-atomic="true" class="flex flex-col items-center gap-3.5">
			<div v-if="tone === 'loading'" class="spinner" aria-hidden="true"></div>
			<p v-else-if="tone === 'error'" class="eyebrow text-seal">{{ eyebrow }}</p>
			<div v-else-if="tone === 'empty'" class="empty-mark" aria-hidden="true">+</div>
			<div v-else-if="tone === 'info'" class="empty-mark" aria-hidden="true">i</div>
			<slot name="mark" />
			<component :is="tone === 'empty' ? 'h3' : 'h2'" v-if="title || $slots.title" :class="tone === 'empty' ? 'empty-title' : 'sheet-title mt-2'">
				<slot name="title">{{ title }}</slot>
			</component>
			<p v-if="message" :class="tone === 'empty' ? 'empty-text' : 'max-w-[42ch] text-sm leading-7 text-slate-600'">{{ message }}</p>
			<slot />
		</div>
		<div v-if="$slots.actions" class="mt-6 flex flex-wrap items-center justify-center gap-3">
			<slot name="actions" />
		</div>
	</div>
</template>
