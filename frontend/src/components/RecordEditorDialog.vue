<script setup>
import { computed, reactive, watch } from "vue"
import { Button } from "frappe-ui"
import DialogFrame from "./DialogFrame.vue"
import FormField from "./FormField.vue"
import NoticeBar from "./NoticeBar.vue"

const props = defineProps({
	open: { type: Boolean, default: false },
	title: { type: String, required: true },
	description: { type: String, default: "" },
	fields: { type: Array, required: true },
	record: { type: Object, default: null },
	saving: { type: Boolean, default: false },
	error: { type: String, default: "" },
	saveLabel: { type: String, default: "Save changes" },
})

const emit = defineEmits(["update:open", "save"])
const values = reactive({})
const trackedDefaults = reactive({})
const dialogOpen = computed({
	get: () => props.open,
	set: (value) => emit("update:open", value),
})

function resetForm() {
	for (const key of Object.keys(values)) delete values[key]
	for (const key of Object.keys(trackedDefaults)) delete trackedDefaults[key]
	for (const field of props.fields) {
		values[field.name] = props.record?.[field.name] ?? (field.type === "checkbox" ? false : "")
	}
	for (const field of props.fields) {
		if (!field.autoDefaultByValue) continue
		const expected = defaultValue(field)
		trackedDefaults[field.name] = expected && values[field.name] === expected ? expected : null
	}
}

function fieldOptions(field) {
	let fieldOptions = field.optionsByValue
		? field.optionsByValue[values[field.dependsOn?.[0]]] || []
		: field.options || []
	if (field.optionsOverride && Object.entries(field.optionsOverride.when).every(([name, value]) => values[name] === value)) {
		fieldOptions = field.optionsOverride.options
	}
	return fieldOptions
}

function isFieldVisible(field) {
	return !field.optionsByValue || fieldOptions(field).length > 0
}

function defaultValue(field) {
	let value = field.autoDefaultByValue[values.customer_type] || ""
	for (const override of field.autoDefaultOverrides || []) {
		if (Object.entries(override.when).every(([name, expected]) => values[name] === expected)) {
			value = override.value
		}
	}
	return value
}

function updateValue(field, value) {
	values[field.name] = value
	const changedFields = new Set([field.name])
	let foundDependent
	do {
		foundDependent = false
		for (const dependent of props.fields) {
			if (
				!dependent.dependsOn?.some((dependency) => changedFields.has(dependency)) ||
				!values[dependent.name]
			) {
				continue
			}
			if (!fieldOptions(dependent).some((option) => option.value === values[dependent.name])) {
				values[dependent.name] = ""
				changedFields.add(dependent.name)
				foundDependent = true
			}
		}
	} while (foundDependent)

	for (const candidate of props.fields) {
		if (!candidate.autoDefaultByValue || !candidate.autoDefaultFor?.includes(field.name)) continue
		const next = defaultValue(candidate)
		const previous = trackedDefaults[candidate.name]
		if (next) {
			if (previous && values[candidate.name] === previous && previous !== next) {
				values[candidate.name] = next
			} else if (!values[candidate.name]) {
				values[candidate.name] = next
			}
			trackedDefaults[candidate.name] = values[candidate.name] === next ? next : null
		}
	}
}

watch(() => props.open, (open) => {
	if (open) resetForm()
})

function submit() {
	emit("save", { name: props.record?.name || null, values: { ...values } })
}
</script>

<template>
	<DialogFrame v-model:open="dialogOpen" :title="title" :description="description" size="lg">
		<template #title>
			<div>
				<p class="eyebrow">{{ record ? "Edit record" : "New record" }}</p>
				<h2 class="mt-0.5 font-display text-[1.6rem] font-normal leading-[1.1] tracking-[-0.01em] text-ink">{{ title }}</h2>
			</div>
		</template>
		<NoticeBar v-if="error" type="error" :message="error" :dismissible="false" />
		<FormField
			v-for="field in fields"
			v-show="isFieldVisible(field)"
			:key="field.name"
			:field="field"
			:model-value="values[field.name]"
			:field-options="fieldOptions(field)"
			@update:model-value="updateValue(field, $event)"
		/>
		<template #actions="{ close }">
			<Button class="audit-btn audit-btn--secondary" :disabled="saving" @click="close">Cancel</Button>
			<Button class="audit-btn audit-btn--primary" :disabled="saving" @click="submit">
				{{ saving ? "Saving…" : saveLabel }}
			</Button>
		</template>
	</DialogFrame>
</template>
