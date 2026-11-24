from html import escape

import frappe
from frappe import _
from frappe.website.page_renderers.base_renderer import BaseRenderer


class AuditPortalRenderer(BaseRenderer):
	def can_render(self):
		return self.path == "portal"

	def render(self):
		request_path = frappe.request.path.rstrip("/")
		if request_path == "/client-portal" and frappe.session.user == "Guest":
			frappe.local.flags.redirect_location = f"/login?redirect-to={request_path}"
			raise frappe.Redirect

		frappe.local.no_cache = 1
		csrf_token = escape(frappe.sessions.get_csrf_token(), quote=True)
		user = escape(frappe.session.user or "Guest", quote=True)
		page_title = _("Request portal access") if request_path == "/signup" else _("Client portal")
		js_path = "/assets/audit_portal/frontend/assets/portal.js"
		css_path = "/assets/audit_portal/frontend/assets/portal.css"

		html = f"""<!doctype html>
<html lang="{escape(frappe.local.lang or 'en', quote=True)}">
	<head>
		<meta charset="UTF-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<meta name="theme-color" content="#17243a">
		<title>{escape(page_title)}</title>
		<link rel="stylesheet" href="{css_path}">
		<script type="module" src="{js_path}"></script>
	</head>
	<body>
		<div id="app" data-csrf-token="{csrf_token}" data-user="{user}"></div>
	</body>
</html>"""

		return self.build_response(
			html,
			headers={"Cache-Control": "no-store"},
		)
