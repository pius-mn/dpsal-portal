import path from "node:path"
import { fileURLToPath } from "node:url"
import vue from "@vitejs/plugin-vue"
import frappeui from "frappe-ui/vite"
import { defineConfig } from "vite"

const frontendDirectory = path.dirname(fileURLToPath(import.meta.url))

function dropUnusedFontAssets() {
	return {
		name: "audit-portal-drop-unused-font-assets",
		generateBundle(_options, bundle) {
			for (const fileName of Object.keys(bundle)) {
				if (/Inter(?:-Italic)?\.var-.*\.woff2$/.test(fileName)) delete bundle[fileName]
			}
		},
	}
}

function portalDevPages() {
	return {
		name: "audit-portal-dev-pages",
		configureServer(server) {
			server.middlewares.use(async (request, response, next) => {
				const pathname = new URL(request.url || "/", "http://localhost").pathname.replace(/\/+$/, "") || "/"
				if (request.method !== "GET" || !["/client-portal", "/signup"].includes(pathname)) {
					next()
					return
				}

				const html = `<!doctype html>
<html lang="en">
	<head>
		<meta charset="UTF-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<title>Audit Portal</title>
	</head>
	<body>
		<div id="app" data-csrf-token="" data-user="Guest"></div>
		<script type="module" src="/src/main.js"></script>
	</body>
</html>`

				try {
					const transformed = await server.transformIndexHtml(request.url || pathname, html)
					response.statusCode = 200
					response.setHeader("Content-Type", "text/html")
					response.end(transformed)
				} catch (error) {
					next(error)
				}
			})
		},
	}
}

export default defineConfig(({ command }) => ({
	root: frontendDirectory,
	base: command === "build" ? "/assets/audit_portal/frontend/" : "/",
	plugins: [
		dropUnusedFontAssets(),
		portalDevPages(),
		frappeui({
			jinjaBootData: false,
			frappeProxy: process.env.FRAPPE_UI_DEV_PORT
				? { port: Number(process.env.FRAPPE_UI_DEV_PORT) }
				: true,
			buildConfig: false,
		}),
		vue(),
	],
	appType: "custom",
	server: {
		host: "127.0.0.1",
	},
	build: {
		outDir: path.resolve(frontendDirectory, "../audit_portal/public/frontend"),
		emptyOutDir: true,
		rollupOptions: {
			input: path.resolve(frontendDirectory, "src/main.js"),
			output: {
				entryFileNames: "assets/portal.js",
				chunkFileNames: "assets/[name]-[hash].js",
				assetFileNames: (asset) =>
					asset.name?.endsWith(".css") ? "assets/portal.css" : "assets/[name]-[hash][extname]",
			},
		},
	},
}))
