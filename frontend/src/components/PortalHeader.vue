<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { Button } from "frappe-ui"

const props = defineProps({
	user: { type: String, default: "Guest" },
	context: { type: String, default: "portal" },
	navItems: { type: Array, default: () => [] },
	activeNav: { type: String, default: "overview" },
})

const emit = defineEmits(["navigate"])

const mobileNavOpen = ref(false)
const sidebar = ref(null)
let previousOverflow = ""
let returnFocusTo = null

const navGroups = computed(() => {
	const groups = []
	for (const item of props.navItems) {
		const label = item.group || "Workspace"
		let group = groups.find((entry) => entry.label === label)
		if (!group) {
			group = { label, items: [] }
			groups.push(group)
		}
		group.items.push(item)
	}
	return groups
})

function hrefFor(item) {
	const base = props.context === "signup" ? "/signup" : "/client-portal"
	return item.id === "overview" ? base : `${base}?tab=${encodeURIComponent(item.id)}`
}

function openMobileNav() {
	returnFocusTo = document.activeElement
	mobileNavOpen.value = true
	nextTick(() => sidebar.value?.querySelector("a, button")?.focus())
}

function closeMobileNav({ restoreFocus = true } = {}) {
	mobileNavOpen.value = false
	if (restoreFocus) nextTick(() => returnFocusTo?.focus?.())
}

function navigate(item) {
	emit("navigate", item.id)
	closeMobileNav({ restoreFocus: false })
	nextTick(() => {
		const topLink = document.querySelector(`[data-top-nav="${item.id}"]`)
		const target = topLink?.getClientRects().length
			? topLink
			: document.querySelector("#portal-content")
		;(target || returnFocusTo)?.focus?.()
	})
}

function onKeydown(event) {
	if (!mobileNavOpen.value) return
	if (event.key === "Escape") {
		event.preventDefault()
		closeMobileNav()
		return
	}
	if (event.key !== "Tab" || !sidebar.value) return
	const focusable = [...sidebar.value.querySelectorAll("a[href], button:not([disabled])")]
	if (!focusable.length) return
	const first = focusable[0]
	const last = focusable[focusable.length - 1]
	if (event.shiftKey && document.activeElement === first) {
		event.preventDefault()
		last.focus()
	} else if (!event.shiftKey && document.activeElement === last) {
		event.preventDefault()
		first.focus()
	}
}

watch(mobileNavOpen, (open) => {
	if (open) {
		previousOverflow = document.body.style.overflow
		document.body.style.overflow = "hidden"
	} else {
		document.body.style.overflow = previousOverflow
	}
})

onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => {
	window.removeEventListener("keydown", onKeydown)
	document.body.style.overflow = previousOverflow
})
</script>

<template>
	<header class="sticky top-0 z-40 border-b border-line bg-paper/92 backdrop-blur-md">
		<div class="shell-max flex min-h-[4.5rem] items-center gap-4 max-sm:min-h-16 max-sm:gap-2.5">
			<a :href="context === 'signup' ? '/signup' : '/client-portal'" class="group inline-flex items-center gap-3 rounded-[10px] text-inherit no-underline max-sm:gap-2.5">
				<span class="brand-seal" aria-hidden="true">A</span>
				<span>
					<span class="block whitespace-nowrap text-[0.9rem] font-bold leading-[1.15] tracking-[-0.01em] max-sm:text-[0.85rem]">{{ context === "signup" ? "Audit Portal" : "Client workspace" }}</span>
					<span class="mt-0.5 block font-mono text-[0.5625rem] uppercase tracking-[0.18em] text-muted max-sm:hidden">{{ context === "signup" ? "Client access" : "Audit Portal" }}</span>
				</span>
			</a>

			<nav v-if="navItems.length" class="hidden min-w-0 flex-1 items-center justify-center gap-0.5 xl:flex" aria-label="Workspace pages">
				<a
					v-for="item in navItems"
					:key="item.id"
					:href="hrefFor(item)"
					:data-top-nav="item.id"
					:aria-current="activeNav === item.id ? 'page' : undefined"
					class="relative inline-flex items-center gap-1.5 whitespace-nowrap rounded-[0.5rem] px-2.5 py-2 text-[0.8125rem] font-semibold text-muted no-underline transition hover:bg-canvas-soft hover:text-ink aria-[current=page]:text-ink"
					@click.prevent="navigate(item)"
				>
					<span v-if="activeNav === item.id" class="size-1 rounded-full bg-brass" aria-hidden="true"></span>
					<span>{{ item.shortLabel || item.label }}</span>
					<span v-if="item.count !== undefined" class="figure rounded-[0.25rem] px-[0.35rem] py-[0.18rem] text-[0.5625rem] font-medium tracking-[0.02em]" :class="activeNav === item.id ? 'bg-bottle-soft text-bottle' : 'bg-line text-muted-strong'">{{ item.count }}</span>
					<span v-if="activeNav === item.id" class="absolute inset-x-2 bottom-0 h-[2px] rounded-full bg-bottle" aria-hidden="true"></span>
				</a>
			</nav>

			<div class="ml-auto flex items-center gap-[0.9rem] max-sm:gap-2.5">
				<template v-if="user !== 'Guest'">
					<span class="max-w-64 truncate text-[0.8125rem] text-muted max-md:hidden">{{ user }}</span>
					<a v-if="context === 'portal'" href="/logout" class="whitespace-nowrap border-b border-transparent pb-px text-[0.8125rem] font-semibold text-bottle no-underline transition-colors hover:border-brass hover:text-bottle-deep max-sm:text-xs">Sign out</a>
					<a v-else href="/client-portal" class="whitespace-nowrap border-b border-transparent pb-px text-[0.8125rem] font-semibold text-bottle no-underline transition-colors hover:border-brass hover:text-bottle-deep max-sm:text-xs">Open client workspace</a>
				</template>
				<template v-else>
					<a href="/login?redirect-to=/client-portal" class="whitespace-nowrap border-b border-transparent pb-px text-[0.8125rem] font-semibold text-bottle no-underline transition-colors hover:border-brass hover:text-bottle-deep max-sm:text-xs">
						{{ context === "signup" ? "Already a client? Sign in" : "Sign in" }}
					</a>
					<a v-if="context === 'portal'" href="/signup" class="audit-btn audit-btn--secondary audit-btn--sm max-sm:min-h-[1.95rem] max-sm:px-[0.65rem] max-sm:py-[0.35rem] max-sm:text-[0.6875rem]">Request access</a>
				</template>
				<Button
					v-if="navItems.length"
					label="Open navigation"
					:aria-expanded="mobileNavOpen"
					aria-controls="portal-sidebar"
					class="audit-btn audit-btn--secondary audit-btn--sm xl:!hidden"
					@click="openMobileNav"
				>
					<template #icon>
						<svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
							<path d="M4 7h16M4 12h16M4 17h16" />
						</svg>
					</template>
				</Button>
			</div>
		</div>

		<Teleport to="body">
			<Transition
				enter-active-class="transition-opacity duration-200"
				enter-from-class="opacity-0"
				leave-active-class="transition-opacity duration-150"
				leave-to-class="opacity-0"
			>
				<div v-if="mobileNavOpen" class="fixed inset-0 z-50 bg-ink/45 backdrop-blur-[2px]" aria-hidden="true" @click="closeMobileNav()" />
			</Transition>

			<Transition
				enter-active-class="transition-transform duration-200 ease-out"
				enter-from-class="-translate-x-full"
				leave-active-class="transition-transform duration-150 ease-in"
				leave-to-class="-translate-x-full"
			>
				<div
					v-if="mobileNavOpen"
					id="portal-sidebar"
					ref="sidebar"
					class="fixed inset-y-0 left-0 z-50 flex w-[min(21rem,88vw)] overflow-hidden bg-paper shadow-[24px_0_60px_-32px_rgb(8_25_20_/_65%)]"
					role="dialog"
					aria-modal="true"
					aria-label="Workspace navigation"
				>
					<div class="dossier-spine" aria-hidden="true">
						<span class="absolute inset-x-0 top-6 rotate-180 text-center font-mono text-[0.5625rem] uppercase tracking-[0.2em] text-[#e7f0eb]/60 [writing-mode:vertical-rl]">Client dossier</span>
						<span class="absolute bottom-6 left-1/2 size-1.5 -translate-x-1/2 rounded-full bg-brass"></span>
					</div>

					<div class="flex min-w-0 flex-1 flex-col">
						<div class="flex items-start justify-between gap-3 border-b border-line px-5 py-5">
							<div>
								<p class="eyebrow eyebrow--brass">Client dossier</p>
								<p class="mt-1 font-display text-xl font-normal leading-tight text-ink">Workspace index</p>
							</div>
							<Button label="Close navigation" class="audit-btn audit-btn--secondary audit-btn--sm" @click="closeMobileNav()">
								<template #icon>
									<svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
										<path d="M6 6l12 12M18 6L6 18" />
									</svg>
								</template>
							</Button>
						</div>

						<nav class="flex-1 overflow-y-auto px-3 py-4" aria-label="Workspace pages">
							<div v-for="group in navGroups" :key="group.label" class="mb-5">
								<p class="eyebrow px-2">{{ group.label }}</p>
								<div class="mt-2 space-y-1">
									<a
										v-for="item in group.items"
										:key="item.id"
										:href="hrefFor(item)"
										:aria-current="activeNav === item.id ? 'page' : undefined"
										class="group flex items-center justify-between gap-3 rounded-[0.65rem] border border-transparent px-3 py-2.5 text-sm font-semibold text-muted no-underline transition hover:border-line hover:bg-canvas-soft hover:text-ink aria-[current=page]:border-line aria-[current=page]:bg-bottle-soft aria-[current=page]:text-bottle-deep"
										@click.prevent="navigate(item)"
									>
										<span class="flex min-w-0 items-center gap-2.5">
											<span class="size-1.5 shrink-0 rounded-full" :class="activeNav === item.id ? 'bg-brass' : 'bg-line-strong'" aria-hidden="true"></span>
											<span class="truncate">{{ item.label }}</span>
										</span>
										<span v-if="item.count !== undefined" class="figure shrink-0 rounded-[0.25rem] px-[0.35rem] py-[0.18rem] text-[0.5625rem] font-medium tracking-[0.02em]" :class="activeNav === item.id ? 'bg-bottle text-white' : 'bg-line text-muted-strong'">{{ item.count }}</span>
									</a>
								</div>
							</div>
						</nav>

						<div class="border-t border-line px-5 py-4">
							<p class="truncate text-xs text-muted">{{ user }}</p>
							<a href="/logout" class="text-action mt-2">Sign out</a>
						</div>
					</div>
				</div>
			</Transition>
		</Teleport>
	</header>
</template>
