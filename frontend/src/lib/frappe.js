const csrfToken = () => document.querySelector("#app")?.dataset.csrfToken || ""

export async function callFrappe(method, { args, method: httpMethod = "GET" } = {}) {
	const url = new URL(`/api/method/${method}`, window.location.origin)
	const options = {
		method: httpMethod,
		credentials: "same-origin",
		headers: {
			Accept: "application/json",
		},
	}

	if (httpMethod === "GET" && args) {
		for (const [key, value] of Object.entries(args)) {
			if (value !== undefined && value !== null) {
				url.searchParams.set(key, value)
			}
		}
	} else if (args) {
		options.headers["Content-Type"] = "application/json"
		options.headers["X-Frappe-CSRF-Token"] = csrfToken()
		options.body = JSON.stringify(args)
	}

	const response = await fetch(url, options)
	let payload
	try {
		payload = await response.json()
	} catch {
		throw new Error(`The server returned an invalid response (${response.status}).`)
	}

	if (!response.ok || payload.exc) {
		throw new Error(getErrorMessage(payload, response.status))
	}

	return payload.message
}

export async function uploadFrappe(method, { args, file }) {
	const url = new URL(`/api/method/${method}`, window.location.origin)
	for (const [key, value] of Object.entries(args || {})) {
		if (value !== undefined && value !== null) url.searchParams.set(key, value)
	}
	const formData = new FormData()
	formData.append("file", file)
	const response = await fetch(url, {
		method: "POST",
		credentials: "same-origin",
		headers: {
			Accept: "application/json",
			"X-Frappe-CSRF-Token": csrfToken(),
		},
		body: formData,
	})
	let payload
	try {
		payload = await response.json()
	} catch {
		throw new Error(`The server returned an invalid response (${response.status}).`)
	}
	if (!response.ok || payload.exc) throw new Error(getErrorMessage(payload, response.status))
	return payload.message
}

function getErrorMessage(payload, status) {
	if (payload._server_messages) {
		try {
			const messages = JSON.parse(payload._server_messages)
			const firstMessage = JSON.parse(messages[0])
			if (firstMessage.message) return firstMessage.message
		} catch {
			// Fall through to the regular message below.
		}
	}

	if (typeof payload.message === "string") return payload.message
	if (status === 403) return "You do not have permission to access this information."
	return `The request failed (${status}). Please try again.`
}
