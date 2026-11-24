import autoprefixer from "autoprefixer"
import tailwindcss from "tailwindcss"

function stripUnusedFontFaces() {
	return {
		postcssPlugin: "audit-portal-strip-unused-font-faces",
		AtRule: {
			"font-face": (atRule) => {
				const body = atRule.nodes?.map((node) => node.toString()).join("\n") || ""
				if (/font-family:\s*['"]?(?:Inter|InterVar)['"]?/i.test(body)) atRule.remove()
			},
		},
	}
}

export default {
	plugins: [stripUnusedFontFaces(), tailwindcss(), autoprefixer()],
}
