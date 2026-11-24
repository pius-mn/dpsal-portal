export function formatCurrency(amount, currency) {
	try {
		return new Intl.NumberFormat(undefined, {
			style: "currency",
			currency: currency || "USD",
		}).format(Number(amount) || 0)
	} catch {
		return `${currency || ""} ${(Number(amount) || 0).toFixed(2)}`.trim()
	}
}

export function formatDate(value, fallback = "Not set") {
	if (!value) return fallback
	const normalized = String(value).includes(" ") ? String(value).replace(" ", "T") : String(value)
	const date = normalized.includes("T") ? new Date(normalized) : new Date(`${normalized}T00:00:00`)
	if (Number.isNaN(date.getTime())) return String(value)
	return new Intl.DateTimeFormat(undefined, {
		day: "numeric",
		month: "short",
		year: "numeric",
	}).format(date)
}

export function display(value, fallback = "Not provided") {
	return value === null || value === undefined || value === "" ? fallback : value
}

export function options(values) {
	return (values || []).map((value) => {
		if (typeof value === "string") return { label: value, value }
		return {
			label: value.label || value.name || String(value),
			value: value.value ?? value.name ?? value,
		}
	})
}
