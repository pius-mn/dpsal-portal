import path from "node:path"
import { createRequire } from "node:module"
import frappeUIPreset from "frappe-ui/tailwind"

const require = createRequire(import.meta.url)
const frappeUIRoot = path.resolve(path.dirname(require.resolve("frappe-ui/tailwind")), "..")
const frappeUIGlob = (pattern) => path.join(frappeUIRoot, pattern).split(path.sep).join("/")

const frappeUIContent = [
	"src/components/Button/**/*.{vue,js,ts}",
	"src/components/Spinner/**/*.{vue,js,ts}",
	"src/components/Tooltip/**/*.{vue,js,ts}",
	"src/components/Dialog/**/*.{vue,js,ts}",
	"src/components/Dialogs.vue",
	"src/components/FrappeUIProvider/**/*.{vue,js,ts}",
	"src/components/InputLabeling/**/*.{vue,js,ts}",
	"src/components/ItemListRow/**/*.{vue,js,ts}",
	"src/components/Select/**/*.{vue,js,ts}",
	"src/components/TextInput/**/*.{vue,js,ts}",
	"src/components/Textarea/**/*.{vue,js,ts}",
	"src/components/Toast/**/*.{vue,js,ts}",
	"src/components/shared/**/*.{vue,js,ts}",
	"src/composables/**/*.{vue,js,ts}",
	"src/utils/dialog.ts",
	"src/utils/config.ts",
	"src/utils/iconString.ts",
	"src/utils/pageMeta.ts",
].map(frappeUIGlob)

export default {
	presets: [frappeUIPreset],
	content: [...frappeUIContent, "./*.html", "./src/**/*.{vue,js}"],
	theme: {
		extend: {
			colors: {
				canvas: { DEFAULT: "#edf0ee", soft: "#f5f7f5" },
				paper: "#ffffff",
				ink: { DEFAULT: "#12211d", soft: "#35443f" },
				muted: { DEFAULT: "#63716c", strong: "#4a5953" },
				line: { DEFAULT: "#dbe2de", strong: "#c4cfc9" },
				bottle: { DEFAULT: "#14483c", deep: "#0b332b", soft: "#e6efeb" },
				brass: { DEFAULT: "#a2833f", strong: "#856a2f", soft: "#f5eedf" },
				seal: { DEFAULT: "#8f3a30", soft: "#f8eae7" },
				focus: "#2f7a63",
			},
			fontFamily: {
				sans: ['"Public Sans"', '"Public Sans Fallback"', '"Segoe UI"', "sans-serif"],
				display: ['"Libre Caslon Display"', '"Libre Caslon Fallback"', '"Iowan Old Style"', '"Palatino Linotype"', "Georgia", "serif"],
				mono: ['"IBM Plex Mono"', '"SFMono-Regular"', "Consolas", '"Liberation Mono"', "monospace"],
			},
			boxShadow: {
				sheet: "0 1px 0 rgb(18 33 29 / 3%), 0 24px 48px -38px rgb(18 33 29 / 45%)",
				lift: "0 10px 24px -16px rgb(11 51 43 / 55%)",
			},
		},
	},
}
