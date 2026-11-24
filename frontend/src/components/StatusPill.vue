<script setup>
import { computed } from "vue"

const props = defineProps({
	status: { type: String, default: "" },
})

const tones = {
	positive: "border-[#c7ded2] bg-bottle-soft text-[#1c5a44]",
	warn: "border-[#e7d6b4] bg-brass-soft text-[#7c5c18]",
	danger: "border-[#e6c7c1] bg-seal-soft text-[#7c3028]",
	info: "border-[#c6d8d0] bg-[#e8f1ed] text-[#1a5b4b]",
	neutral: "border-line bg-[#eef1ef] text-[#5b6863]",
}

const states = {
	"Pending Review": { label: "Waiting for review", tone: "warn" },
	"Not Submitted": { label: "No file yet", tone: "neutral" },
	Verified: { label: "Verified", tone: "positive" },
	Rejected: { label: "Needs an update", tone: "danger" },
	Open: { label: "Ready for review", tone: "info" },
	Closed: { label: "Cancelled", tone: "neutral" },
	Overdue: { label: "Past due", tone: "danger" },
	Ordered: { label: "Accepted", tone: "positive" },
	Lost: { label: "Declined", tone: "danger" },
	Replied: { label: "Response received", tone: "neutral" },
	"Partially Ordered": { label: "Partly accepted", tone: "warn" },
	Paid: { label: "Paid", tone: "positive" },
	Unpaid: { label: "Payment due", tone: "warn" },
}

const state = computed(() => states[props.status] || { label: props.status || "Not set", tone: "neutral" })
</script>

<template>
	<span class="status-stamp" :class="tones[state.tone]">{{ state.label }}</span>
</template>
