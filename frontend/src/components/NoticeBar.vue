<script setup>
defineProps({
	type: { type: String, default: "info" },
	message: { type: String, default: "" },
	dismissible: { type: Boolean, default: true },
})

defineEmits(["dismiss"])
</script>

<template>
	<div class="notice" :class="`notice--${type}`" :role="type === 'error' ? 'alert' : 'status'">
		<p><slot>{{ message }}</slot></p>
		<button v-if="dismissible" class="notice-dismiss" aria-label="Dismiss message" @click="$emit('dismiss')">×</button>
	</div>
</template>
