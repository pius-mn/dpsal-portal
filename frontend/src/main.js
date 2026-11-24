import { createApp, defineAsyncComponent, h } from "vue"
import "./style.css"

const LoadingApp = {
	render: () =>
		h(
			"div",
			{
				class: "grid min-h-screen place-items-center bg-canvas px-6 text-center text-sm text-muted",
				role: "status",
				"aria-live": "polite",
			},
			"Loading Audit Portal…",
		),
}

const pages = {
	"/signup": () => import("./pages/SignupApp.vue"),
	"/client-portal": () => import("./pages/PortalApp.vue"),
}

const root = document.querySelector("#app")

if (root) {
	const route = window.location.pathname.replace(/\/+$/, "")
	const page = defineAsyncComponent({
		loader: pages[route] || pages["/client-portal"],
		loadingComponent: LoadingApp,
	})
	document.querySelector('meta[name="theme-color"]')?.setAttribute("content", "#14483c")
	document.title = {
		"/signup": "Request access · Audit Portal",
		"/client-portal": "Client dossier · Audit Portal",
	}[route] || "Client dossier · Audit Portal"
	createApp(page).mount(root)
}
