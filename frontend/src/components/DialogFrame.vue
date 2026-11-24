<script setup>
import { computed } from "vue"
import { Dialog } from "frappe-ui"

const props = defineProps({
	open: { type: Boolean, default: false },
	title: { type: String, default: "" },
	eyebrow: { type: String, default: "" },
	description: { type: String, default: "" },
	size: { type: String, default: "lg" },
})

const emit = defineEmits(["update:open"])
const dialogOpen = computed({
	get: () => props.open,
	set: (value) => emit("update:open", value),
})
</script>

<template>
	<Dialog v-model:open="dialogOpen" :size="size">
		<template #title>
			<slot name="title">
				<div>
					<p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
					<h2 class="mt-0.5 font-display text-[1.6rem] font-normal leading-[1.1] tracking-[-0.01em] text-ink">{{ title }}</h2>
				</div>
			</slot>
		</template>
		<div class="space-y-4 pb-2">
			<Dialog.Description as-child>
				<p class="m-0 text-[0.8125rem] leading-relaxed text-muted">{{ description }}</p>
			</Dialog.Description>
			<slot />
		</div>
		<template #actions="{ close }">
			<div class="flex flex-wrap justify-end gap-2.5">
				<slot name="actions" :close="close" />
			</div>
		</template>
	</Dialog>
</template>
