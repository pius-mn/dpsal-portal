<script setup>
defineProps({
	eyebrow: { type: String, default: "" },
	title: { type: String, default: "" },
	description: { type: String, default: "" },
	titleId: { type: String, default: "" },
	level: { type: Number, default: 2 },
})
</script>

<template>
	<div class="sheet-head">
		<div class="min-w-0">
			<p v-if="eyebrow" class="eyebrow eyebrow--brass">{{ eyebrow }}</p>
			<component :is="`h${level}`" v-if="title || $slots.title" :id="titleId || undefined" class="sheet-title mt-2">
				<slot name="title">{{ title }}</slot>
			</component>
			<p v-if="description || $slots.description" class="sheet-sub">
				<slot name="description">{{ description }}</slot>
			</p>
		</div>
		<div v-if="$slots.actions || $slots.meta" class="flex flex-wrap items-center gap-x-4 gap-y-2">
			<slot name="meta" />
			<div class="flex items-center gap-3">
				<slot name="actions" />
			</div>
		</div>
	</div>
</template>
