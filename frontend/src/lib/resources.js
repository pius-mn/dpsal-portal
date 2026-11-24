import { createResource } from "frappe-ui"
import { callFrappe, uploadFrappe } from "./frappe"

export function createPortalResource(method, options = {}) {
	return createResource({
		url: `/api/method/${method}`,
		method: options.method || "GET",
		params: options.params || null,
		initialData: options.initialData ?? null,
		auto: options.auto || false,
		transform: options.transform,
		onFetch: options.onFetch,
		onSuccess: options.onSuccess,
		onData: options.onData,
		onError: options.onError,
		resourceFetcher: options.resourceFetcher || portalFetcher,
	})
}

export function createUploadResource(method) {
	return createPortalResource(method, {
		method: "POST",
		resourceFetcher: ({ params }) => uploadFrappe(method, params),
	})
}

export async function fetchResource(resource, params, fallback) {
	try {
		return await resource.fetch(params)
	} catch (error) {
		throw new Error(friendlyError(error, fallback))
	}
}

function portalFetcher({ url, method, params }) {
	return callFrappe(String(url).replace(/^\/api\/method\//, ""), {
		method: method || "GET",
		args: params || undefined,
	})
}

function friendlyError(error, fallback) {
	if (typeof error?.message === "string" && error.message) return error.message
	return fallback || "Something went wrong. Please try again."
}
