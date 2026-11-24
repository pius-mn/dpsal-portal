<script setup>
import { Button } from "frappe-ui"
import SheetHeader from "./SheetHeader.vue"
import StatePanel from "./StatePanel.vue"

defineProps({
	title: { type: String, required: true },
	eyebrow: { type: String, default: "Records" },
	description: { type: String, default: "" },
	items: { type: Array, default: () => [] },
	emptyTitle: { type: String, required: true },
	emptyDescription: { type: String, required: true },
	addLabel: { type: String, required: true },
	loading: { type: Boolean, default: false },
	hideAdd: { type: Boolean, default: false },
})

const emit = defineEmits(["add"])
</script>

<template>
	<section class="sheet">
		<SheetHeader :eyebrow="eyebrow" :title="title" :description="description">
			<template #meta>
				<span v-if="items.length" class="rounded-[0.3rem] border border-line bg-canvas-soft px-1.5 py-1 font-mono text-[0.625rem] font-medium text-muted">{{ items.length }}</span>
			</template>
			<template #actions>
				<Button v-if="!hideAdd" class="audit-btn audit-btn--primary" :disabled="loading" @click="emit('add')">{{ addLabel }}</Button>
			</template>
		</SheetHeader>
		<StatePanel v-if="loading" tone="loading" :sheet="false" dense message="Loading your information…" />
		<div v-else-if="items.length" class="flex flex-col">
			<article v-for="item in items" :key="item.name" class="flex flex-col gap-4 border-b border-[#eef2ef] px-6 py-[1.15rem] transition-colors last:border-b-0 hover:bg-[#f9fbf9] sm:flex-row sm:items-start sm:justify-between">
				<div class="min-w-0 flex-1">
					<slot name="summary" :item="item" />
				</div>
				<div class="flex flex-none flex-wrap items-center gap-2.5">
					<slot name="actions" :item="item" />
				</div>
			</article>
		</div>
		<StatePanel v-else tone="empty" :sheet="false" dense :title="emptyTitle" :message="emptyDescription">
			<template v-if="!hideAdd" #actions>
				<Button class="audit-btn audit-btn--secondary" :disabled="loading" @click="emit('add')">{{ addLabel }}</Button>
			</template>
		</StatePanel>
	</section>
</template>
