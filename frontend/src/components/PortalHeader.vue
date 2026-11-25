<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { Button } from "frappe-ui"
import { workspaceNavigation } from "../lib/workspace"

const props = defineProps({
	user: { type: String, default: "Guest" },
	context: { type: String, default: "portal" },
	navItems: { type: Array, default: () => [] },
	activeNav: { type: String, default: "overview" },
	activeSection: { type: String, default: "details" },
	entityName: { type: String, default: "" },
})

const emit = defineEmits(["navigate"])

const mobileNavOpen = ref(false)
const openNavGroup = ref("")
const accountOpen = ref(false)
const expandedMobileGroups = ref([])
const topBar = ref(null)
const sidebar = ref(null)
let previousOverflow = ""
let returnFocusTo = null

const hasNavigation = computed(() => props.navItems.length > 0)
const groups = computed(() => workspaceNavigation(props.navItems))
const overviewItem = computed(() => groups.value[0]?.items?.[0] || null)
const desktopGroups = computed(() => groups.value.slice(1))
const entity = computed(() => props.entityName || (props.context === "signup" ? "" : "DP SAL Portal"))
const accountLabel = computed(() => props.context === "signup" ? "Open client workspace" : "Sign out")
const accountHref = computed(() => props.context === "signup" ? "/client-portal" : "/logout")
const accountInitials = computed(() => {
	const parts = entity.value.replace(/[^A-Za-z0-9 ]/g, "").split(/\s+/).filter(Boolean)
	return (parts.length ? parts.slice(0, 2).map((part) => part[0].toUpperCase()).join("") : "A")
})

function hrefFor(item) {
	const base = props.context === "signup" ? "/signup" : "/client-portal"
	const params = new URLSearchParams()
	if (item.id !== "overview") params.set("tab", item.id)
	if (item.section) params.set("section", item.section)
	const query = params.toString()
	return query ? `${base}?${query}` : base
}

function isItemActive(item) {
	if (item.id !== props.activeNav) return false
	if (item.id === "organization") return (item.section || "details") === (props.activeSection || "details")
	return true
}

function isGroupActive(group) {
	return group.items.some(isItemActive)
}

function supportsHover() {
	return window.matchMedia("(hover: hover) and (pointer: fine)").matches
}

function toggleNavGroup(id) {
	openNavGroup.value = openNavGroup.value === id ? "" : id
	accountOpen.value = false
}

function showNavGroup(id) {
	if (!supportsHover()) return
	openNavGroup.value = id
	accountOpen.value = false
}

function hideNavGroup(id) {
	if (openNavGroup.value === id) openNavGroup.value = ""
}

function onGroupFocusout(event, id) {
	if (!event.currentTarget.contains(event.relatedTarget)) hideNavGroup(id)
}

function focusNavControl(id) {
	nextTick(() => topBar.value?.querySelector(`[data-nav-control="${id}"]`)?.focus())
}

function onGroupKeydown(event, group) {
	if (event.key === "Escape") {
		event.preventDefault()
		hideNavGroup(group.id)
		focusNavControl(group.id)
		return
	}
	if (event.key === "ArrowDown") {
		event.preventDefault()
		openNavGroup.value = group.id
		nextTick(() => {
			const menu = document.getElementById(`portal-nav-${group.id}`)
			menu?.querySelector("a")?.focus()
		})
		return
	}
	if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return

	const ids = groups.value.map((item) => item.id)
	const index = ids.indexOf(group.id)
	const direction = event.key === "ArrowRight" ? 1 : -1
	const next = ids[(index + direction + ids.length) % ids.length]
	event.preventDefault()
	hideNavGroup(group.id)
	focusNavControl(next)
}

function toggleAccount() {
	accountOpen.value = !accountOpen.value
	openNavGroup.value = ""
}

function closeMenus() {
	openNavGroup.value = ""
	accountOpen.value = false
}

function onDocumentPointerDown(event) {
	if (!topBar.value?.contains(event.target)) closeMenus()
}

function toggleMobileGroup(id) {
	expandedMobileGroups.value = expandedMobileGroups.value.includes(id)
		? expandedMobileGroups.value.filter((entry) => entry !== id)
		: [...expandedMobileGroups.value, id]
}

function openMobileNav() {
	returnFocusTo = document.activeElement
	expandedMobileGroups.value = groups.value.filter(isGroupActive).map((group) => group.id)
	closeMenus()
	mobileNavOpen.value = true
	nextTick(() => sidebar.value?.querySelector("a, button")?.focus())
}

function closeMobileNav({ restoreFocus = true } = {}) {
	mobileNavOpen.value = false
	if (restoreFocus) nextTick(() => returnFocusTo?.focus?.())
}

function navigate(item) {
	emit("navigate", item.id, item.section || "details")
	closeMenus()
	closeMobileNav({ restoreFocus: false })
	nextTick(() => {
		const control = topBar.value?.querySelector(`[data-nav-control="${item.id}"]`)
		const target = control?.getClientRects().length ? control : document.querySelector("#portal-content")
		;(target || returnFocusTo)?.focus?.()
	})
}

function onKeydown(event) {
	if (event.key === "Escape") {
		if (mobileNavOpen.value) {
			event.preventDefault()
			closeMobileNav()
			return
		}
		if (openNavGroup.value || accountOpen.value) {
			event.preventDefault()
			const id = openNavGroup.value
			closeMenus()
			if (id) focusNavControl(id)
			return
		}
	}
	if (!mobileNavOpen.value || event.key !== "Tab" || !sidebar.value) return

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

watch(() => props.activeNav, closeMenus)

onMounted(() => {
	document.addEventListener("pointerdown", onDocumentPointerDown)
	document.addEventListener("keydown", onKeydown)
})
onBeforeUnmount(() => {
	document.removeEventListener("pointerdown", onDocumentPointerDown)
	document.removeEventListener("keydown", onKeydown)
	document.body.style.overflow = previousOverflow
})
</script>

<template>
	<header ref="topBar" class="sticky top-0 z-40 border-b border-line bg-paper/92 backdrop-blur-md">
		<div class="shell-max flex min-h-[4.5rem] items-center gap-3 max-sm:min-h-16 max-sm:gap-2.5">
			<a :href="context === 'signup' ? '/signup' : '/client-portal'" class="group inline-flex items-center gap-3 rounded-[10px] text-inherit no-underline max-sm:gap-2.5">
				<span class="brand-seal" aria-hidden="true">A</span>
				<span>
					<span class="block whitespace-nowrap text-[0.9rem] font-bold leading-[1.15] tracking-[-0.01em] max-sm:text-[0.85rem]">DP SAL Portal</span>
					<span class="mt-0.5 block font-mono text-[0.5625rem] uppercase tracking-[0.18em] text-muted max-sm:hidden">{{ context === "signup" ? "Client access" : "Client workspace" }}</span>
				</span>
			</a>

			<nav v-if="hasNavigation" class="hidden min-w-0 flex-1 items-center justify-center gap-0.5 lg:flex" aria-label="Workspace pages">
				<a
					v-if="overviewItem"
					:href="hrefFor(overviewItem)"
					:data-nav-control="overviewItem.id"
					:aria-current="isItemActive(overviewItem) ? 'page' : undefined"
					class="portal-nav-control"
					@click.prevent="navigate(overviewItem)"
				>Overview</a>

				<div
					v-for="group in desktopGroups"
					:key="group.id"
					class="relative"
					@mouseenter="showNavGroup(group.id)"
					@mouseleave="hideNavGroup(group.id)"
					@focusout="onGroupFocusout($event, group.id)"
				>
					<button
						type="button"
						class="portal-nav-control"
						:data-nav-control="group.id"
						:data-active="isGroupActive(group) ? 'true' : 'false'"
						:aria-expanded="openNavGroup === group.id"
						:aria-controls="`portal-nav-${group.id}`"
						@click="toggleNavGroup(group.id)"
						@keydown="onGroupKeydown($event, group)"
					>
						<span>{{ group.label }}</span>
						<svg viewBox="0 0 12 12" class="size-2.5 transition-transform" :class="openNavGroup === group.id ? 'rotate-180' : ''" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
							<path d="M2 4.5 6 8.5 10 4.5" />
						</svg>
					</button>

					<div
						v-if="openNavGroup === group.id"
						:id="`portal-nav-${group.id}`"
						class="absolute left-0 top-full z-50 w-[min(21rem,calc(100vw-2rem))] pt-2"
						role="menu"
						:aria-label="`${group.label} pages`"
					>
						<div class="overflow-hidden rounded-[0.9rem] border border-line-strong bg-paper shadow-sheet">
							<div class="border-b border-line px-4 py-2.5">
								<p class="eyebrow eyebrow--brass">{{ group.label }}</p>
							</div>
							<div class="p-1.5">
								<a
									v-for="item in group.items"
									:key="`${item.id}-${item.section || 'page'}`"
									:href="hrefFor(item)"
									role="menuitem"
									:aria-current="isItemActive(item) ? 'page' : undefined"
									class="group flex items-start gap-3 rounded-[0.6rem] border border-transparent px-3 py-2.5 no-underline transition hover:border-line hover:bg-canvas-soft aria-[current=page]:border-brass/40 aria-[current=page]:bg-bottle-soft"
									@click.prevent="navigate(item)"
								>
									<span class="min-w-0 flex-1">
										<span class="block whitespace-nowrap text-[0.8125rem] font-semibold" :class="isItemActive(item) ? 'text-bottle-deep' : 'text-ink-soft'">{{ item.label }}</span>
										<span class="mt-0.5 block truncate text-[0.6875rem] leading-normal text-muted">{{ item.description }}</span>
									</span>
									<span v-if="item.count !== undefined" class="figure shrink-0 rounded-[0.25rem] px-[0.35rem] py-[0.18rem] text-[0.5625rem] font-medium tracking-[0.02em]" :class="isItemActive(item) ? 'bg-bottle text-white' : 'bg-line text-muted-strong'">{{ item.count }}</span>
								</a>
							</div>
						</div>
					</div>
				</div>
			</nav>

			<div class="ml-auto flex items-center gap-2 max-sm:gap-2.5">
				<template v-if="user !== 'Guest'">
					<div v-if="context === 'portal'" class="relative">
						<button
							type="button"
							class="flex items-center gap-2 rounded-full border border-line-strong bg-paper px-1.5 py-1.5 transition hover:border-bottle hover:bg-bottle-soft/40"
							:aria-expanded="accountOpen"
							aria-controls="portal-account-menu"
							@click="toggleAccount"
						>
							<span class="grid size-7 shrink-0 place-items-center rounded-full bg-bottle font-display text-[0.75rem] leading-none text-[#f7fbf8]">{{ accountInitials }}</span>
							<span class="hidden min-w-0 text-left xl:block">
								<span class="block max-w-[10rem] truncate font-mono text-[0.5625rem] uppercase tracking-[0.12em] text-muted">{{ entity }}</span>
								<span class="block max-w-[10rem] truncate text-[0.75rem] font-semibold leading-tight text-ink-soft">{{ user }}</span>
							</span>
							<svg viewBox="0 0 12 12" class="size-2.5 shrink-0 text-muted transition-transform" :class="accountOpen ? 'rotate-180' : ''" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
								<path d="M2 4.5 6 8.5 10 4.5" />
							</svg>
						</button>

						<div v-if="accountOpen" id="portal-account-menu" class="absolute right-0 top-full z-50 w-[min(18rem,calc(100vw-2rem))] pt-2">
							<div class="rounded-[0.9rem] border border-line-strong bg-paper p-4 shadow-sheet">
								<p class="eyebrow eyebrow--brass">Client account</p>
								<p class="mt-2 truncate font-display text-[1.15rem] font-normal leading-tight text-ink">{{ entity }}</p>
								<p class="mt-1.5 truncate text-xs text-muted">Signed in as {{ user }}</p>
								<div class="mt-4 border-t border-line pt-3">
									<a href="/logout" class="text-action">Sign out</a>
								</div>
							</div>
						</div>
					</div>
					<a v-else :href="accountHref" class="whitespace-nowrap border-b border-transparent pb-px text-[0.8125rem] font-semibold text-bottle no-underline transition-colors hover:border-brass hover:text-bottle-deep max-sm:text-xs">{{ accountLabel }}</a>
				</template>
				<template v-else>
					<a href="/login?redirect-to=/client-portal" class="whitespace-nowrap border-b border-transparent pb-px text-[0.8125rem] font-semibold text-bottle no-underline transition-colors hover:border-brass hover:text-bottle-deep max-sm:text-xs">
						{{ context === "signup" ? "Already a client? Sign in" : "Sign in" }}
					</a>
					<a v-if="context === 'portal'" href="/signup" class="audit-btn audit-btn--secondary audit-btn--sm max-sm:min-h-[1.95rem] max-sm:px-[0.65rem] max-sm:py-[0.35rem] max-sm:text-[0.6875rem]">Request access</a>
				</template>

				<Button
					v-if="hasNavigation"
					label="Open navigation"
					:aria-expanded="mobileNavOpen"
					aria-controls="portal-sidebar"
					class="audit-btn audit-btn--secondary audit-btn--sm lg:!hidden"
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
					class="fixed inset-y-0 left-0 z-50 flex w-[min(22rem,90vw)] overflow-hidden bg-paper shadow-[24px_0_60px_-32px_rgb(8_25_20_/_65%)]"
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
							<div v-for="group in groups" :key="group.id" class="mb-2">
								<a
									v-if="group.id === 'overview'"
									:href="hrefFor(group.items[0])"
									:aria-current="isGroupActive(group) ? 'page' : undefined"
									class="flex items-center justify-between gap-3 rounded-[0.65rem] border border-transparent px-3 py-2.5 text-sm font-semibold text-muted no-underline transition hover:border-line hover:bg-canvas-soft hover:text-ink aria-[current=page]:border-brass/40 aria-[current=page]:bg-bottle-soft aria-[current=page]:text-bottle-deep"
									@click.prevent="navigate(group.items[0])"
								>
									{{ group.label }}
								</a>
								<template v-else>
									<button
										type="button"
										class="flex w-full items-center justify-between gap-3 rounded-[0.65rem] border border-transparent px-3 py-2.5 text-left text-sm font-semibold transition"
										:class="isGroupActive(group) ? 'border-brass/40 bg-bottle-soft/70 text-bottle-deep' : 'text-muted hover:border-line hover:bg-canvas-soft hover:text-ink'"
										:aria-expanded="expandedMobileGroups.includes(group.id)"
										:aria-controls="`portal-mobile-nav-${group.id}`"
										@click="toggleMobileGroup(group.id)"
									>
										<span>{{ group.label }}</span>
										<svg viewBox="0 0 12 12" class="size-2.5 transition-transform" :class="expandedMobileGroups.includes(group.id) ? 'rotate-180' : ''" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
											<path d="M2 4.5 6 8.5 10 4.5" />
										</svg>
									</button>
									<div v-if="expandedMobileGroups.includes(group.id)" :id="`portal-mobile-nav-${group.id}`" class="ml-5 mt-1 space-y-1 border-l border-line pl-2">
										<a
											v-for="item in group.items"
											:key="`${item.id}-${item.section || 'page'}`"
											:href="hrefFor(item)"
											:aria-current="isItemActive(item) ? 'page' : undefined"
											class="flex items-center justify-between gap-3 rounded-[0.55rem] px-3 py-2 text-[0.8125rem] font-semibold text-muted no-underline transition hover:bg-canvas-soft hover:text-ink aria-[current=page]:bg-bottle-soft aria-[current=page]:text-bottle-deep"
											@click.prevent="navigate(item)"
										>
											<span class="min-w-0 truncate">{{ item.label }}</span>
											<span v-if="item.count !== undefined" class="figure shrink-0 rounded-[0.25rem] px-[0.35rem] py-[0.18rem] text-[0.5625rem] font-medium tracking-[0.02em]" :class="isItemActive(item) ? 'bg-bottle text-white' : 'bg-line text-muted-strong'">{{ item.count }}</span>
										</a>
									</div>
								</template>
							</div>
						</nav>

						<div class="border-t border-line px-5 py-4">
							<p class="truncate font-mono text-[0.5625rem] uppercase tracking-[0.14em] text-muted">{{ entity }}</p>
							<p class="mt-1 truncate text-xs text-muted-strong">{{ user }}</p>
							<a href="/logout" class="text-action mt-2">Sign out</a>
						</div>
					</div>
				</div>
			</Transition>
		</Teleport>
	</header>
</template>
