app_name = "audit_portal"
app_title = "Audit Portal"
app_publisher = "pius"
app_description = "Dpsal client portal"
app_email = "info@ventrionicsystems.co.ke"
app_license = "mit"

# Desk form scripts
doctype_js = {
	"Quotation": "public/js/quotation.js",
	"Customer": "public/js/customer.js",
	"Client Verification Request": "public/js/client_verification_request.js",
}

# Lifecycle hooks
before_install = ["audit_portal.provisioning.ensure_audit_document_reviewer_role"]
before_migrate = ["audit_portal.customizations.setup"]
after_migrate = [
	"audit_portal.customizations.setup_customer_record_tables",
	"audit_portal.provisioning.ensure_audit_client_role",
	"audit_portal.provisioning.ensure_audit_document_reviewer_role",
	"audit_portal.provisioning.ensure_default_document_masters",
]

# Client Portal routing and page renderer
website_route_rules = [
	{"from_route": "/client-portal", "to_route": "portal"},
	{"from_route": "/signup", "to_route": "portal"},
]
page_renderer = ["audit_portal.page_renderer.AuditPortalRenderer"]

# Document events
doc_events = {
	"Customer": {
		"validate": "audit_portal.legal_structure.validate_customer_legal_structure",
	},
	"Client Signup Request": {
		"validate": "audit_portal.provisioning.validate_signup_request",
		"on_update": "audit_portal.provisioning.on_update_signup_request",
	},
	"Quotation": {
		"validate": "audit_portal.transaction_defaults.set_quotation_tax_id",
	},
}
