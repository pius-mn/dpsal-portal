<script setup>
import StatePanel from "./StatePanel.vue"

defineProps({
	columns: { type: Array, required: true },
	items: { type: Array, default: () => [] },
	emptyTitle: { type: String, required: true },
	emptyDescription: { type: String, required: true },
	minWidth: { type: String, default: "min-w-[760px]" },
	rowKey: { type: String, default: "name" },
})
</script>

<template>
	<div class="hidden overflow-x-auto md:block">
		<table class="ledger w-full" :class="minWidth">
			<thead>
				<tr>
					<th v-for="column in columns" :key="column.key" :class="column.headerClass">{{ column.label }}</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="item in items" :key="item[rowKey]">
					<td v-for="column in columns" :key="column.key" :class="column.cellClass">
						<slot :name="`cell-${column.key}`" :item="item">{{ item[column.key] }}</slot>
					</td>
				</tr>
				<tr v-if="items.length === 0">
					<td :colspan="columns.length">
						<StatePanel tone="empty" sheet dense :title="emptyTitle" :message="emptyDescription" />
					</td>
				</tr>
			</tbody>
		</table>
	</div>
	<div class="flex flex-col md:hidden">
		<article v-for="item in items" :key="item[rowKey]" class="border-b border-[#eef2ef] px-[1.4rem] py-[1.15rem] last:border-b-0">
			<slot name="mobile" :item="item" />
		</article>
		<StatePanel v-if="items.length === 0" tone="empty" sheet dense :title="emptyTitle" :message="emptyDescription" />
	</div>
</template>
