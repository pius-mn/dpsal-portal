<script setup>
import { computed } from "vue"
import { Select, Textarea, TextInput } from "frappe-ui"

const props = defineProps({
	field: { type: Object, required: true },
	modelValue: { type: [String, Number, Boolean, Object, File], default: "" },
	fieldOptions: { type: Array, default: null },
})

const emit = defineEmits(["update:modelValue", "change"])
const label = computed(() => (props.field.required ? `${props.field.label} *` : props.field.label))
const resolvedOptions = computed(() => props.fieldOptions || props.field.options || [])

function update(value) {
	emit("update:modelValue", value)
	emit("change", value)
}
</script>

<template>
	<label v-if="field.type === 'checkbox'" class="flex items-start gap-3 rounded-[0.6rem] border border-line p-3 text-[0.8125rem] text-ink-soft">
		<input type="checkbox" class="mt-0.5 size-4 rounded-[0.2rem] border-line-strong text-bottle" :name="field.name" :checked="Boolean(modelValue)" @change="update($event.target.checked)">
		<span>{{ label }}</span>
	</label>

	<label v-else-if="field.type === 'file'" class="block">
		<span class="mb-1.5 block text-[0.8125rem] font-semibold text-ink-soft">{{ label }}</span>
		<input type="file" class="file-field" :name="field.name" :accept="field.accept" @change="update($event.target.files?.[0] || null)">
		<span v-if="modelValue?.name" class="record-note">Selected: {{ modelValue.name }}</span>
	</label>

	<Select
		v-else-if="field.type === 'select'"
		:id="field.name"
		:model-value="modelValue"
		:label="label"
		:options="resolvedOptions"
		:placeholder="field.placeholder || `Choose ${field.label.toLowerCase()}`"
		v-bind="field.inputProps || {}"
		@update:model-value="update"
	/>

	<Textarea
		v-else-if="field.type === 'textarea'"
		:id="field.name"
		:model-value="modelValue"
		:label="label"
		:placeholder="field.placeholder"
		:rows="field.rows || 3"
		:maxlength="field.maxlength"
		v-bind="field.inputProps || {}"
		@update:model-value="update"
	/>

	<TextInput
		v-else
		:id="field.name"
		:model-value="modelValue"
		:label="label"
		:type="field.type || 'text'"
		:name="field.name"
		:placeholder="field.placeholder"
		:required="field.required"
		:step="field.step"
		:maxlength="field.maxlength"
		:autocomplete="field.autocomplete"
		v-bind="field.inputProps || {}"
		@update:model-value="update"
	/>
</template>
