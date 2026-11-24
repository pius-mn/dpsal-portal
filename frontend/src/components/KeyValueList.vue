<script setup>
import { computed } from "vue"
import { display } from "../lib/format"

const props = defineProps({
	items: { type: Array, default: () => [] },
	variant: { type: String, default: "rows" },
})

const listClass = computed(() => ({
	rows: "mt-5 border-t border-line",
	grid: "grid grid-cols-3 gap-x-8 gap-y-[1.35rem] p-6 max-[900px]:grid-cols-2 max-[600px]:grid-cols-1",
	plain: "text-[0.8125rem]",
	cover: "cover-ledger",
}[props.variant]))

const itemClass = computed(() => ({
	rows: "flex items-baseline justify-between gap-4 border-b border-line py-[0.7rem]",
	grid: "min-w-0",
	plain: "flex items-baseline justify-between gap-4 py-[0.3rem]",
	cover: "",
}[props.variant]))

const termClass = computed(() => ({
	rows: "m-0 font-mono text-[0.5625rem] uppercase tracking-[0.12em] text-muted",
	grid: "m-0 font-mono text-[0.5625rem] uppercase tracking-[0.13em] text-muted",
	plain: "text-muted",
	cover: "",
}[props.variant]))

const detailClass = computed(() => ({
	rows: "m-0 min-w-0 truncate text-right text-[0.8125rem] text-ink-soft",
	grid: "mt-1.5 text-sm leading-normal [overflow-wrap:anywhere]",
	plain: "m-0 font-mono tabular-nums text-ink",
	cover: "",
}[props.variant]))
</script>

<template>
	<dl :class="listClass">
		<div v-for="item in items" :key="item.label" :class="itemClass">
			<dt :class="termClass">{{ item.label }}</dt>
			<dd :class="detailClass">
				<slot name="value" :item="item">{{ display(item.value, item.fallback) }}</slot>
			</dd>
		</div>
	</dl>
</template>
