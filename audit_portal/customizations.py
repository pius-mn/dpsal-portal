import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOMER_CUSTOM_FIELDS = [
	{
		"fieldname": "custom_audit_profile_section",
		"label": "Audit and Registration Details",
		"fieldtype": "Section Break",
		"insert_after": "customer_type",
	},
	{
		"fieldname": "custom_structure_subcategory",
		"label": "Structure sub-category",
		"fieldtype": "Select",
		"insert_after": "custom_audit_profile_section",
	},
	{
		"fieldname": "custom_structure_subcategory_2",
		"label": "Structure sub-category 2",
		"fieldtype": "Select",
		"insert_after": "custom_structure_subcategory",
	},
	{
		"fieldname": "custom_structure_subcategory_3",
		"label": "Structure sub-category 3",
		"fieldtype": "Select",
		"insert_after": "custom_structure_subcategory_2",
	},
	{
		"fieldname": "custom_structure_details",
		"label": "Additional structure details",
		"fieldtype": "Data",
		"insert_after": "custom_structure_subcategory_3",
	},
	{
		"fieldname": "custom_governing_law",
		"label": "Governing Law",
		"fieldtype": "Data",
		"insert_after": "custom_structure_details",
	},
	{
		"fieldname": "custom_regulating_authority",
		"label": "Regulating Authority",
		"fieldtype": "Select",
		"options": "\nRDB\nRGB\nRCA\nRRA\nNotary\nNone",
		"insert_after": "custom_governing_law",
	},
	{
		"fieldname": "custom_registration_no",
		"label": "Registration Number",
		"fieldtype": "Data",
		"insert_after": "custom_regulating_authority",
	},
	{
		"fieldname": "custom_audit_profile_column_break",
		"fieldtype": "Column Break",
		"insert_after": "custom_registration_no",
	},
	{
		"fieldname": "custom_domicile",
		"label": "Domicile",
		"fieldtype": "Select",
		"options": "\nNational\nInternational",
		"insert_after": "custom_audit_profile_column_break",
	},
	{
		"fieldname": "custom_registration_date",
		"label": "Registration Date",
		"fieldtype": "Date",
		"insert_after": "custom_domicile",
	},
	{
		"fieldname": "custom_regulator_reg_date",
		"label": "Regulator Registration Date",
		"fieldtype": "Date",
		"insert_after": "custom_registration_date",
	},
	{
		"fieldname": "custom_regulator_dereg_date",
		"label": "Regulator Deregistration Date",
		"fieldtype": "Date",
		"insert_after": "custom_regulator_reg_date",
	},
	{
		"fieldname": "custom_risk_nationality",
		"label": "Risk Classification",
		"fieldtype": "Select",
		"options": "\nGreen\nYellow\nRed",
		"insert_after": "custom_regulator_dereg_date",
	},
	{
		"fieldname": "custom_service_priority",
		"label": "Service Priority",
		"fieldtype": "Select",
		"options": "\nHigh\nMedium\nLow",
		"insert_after": "custom_risk_nationality",
	},
	{
		"fieldname": "custom_special_attention",
		"label": "Notes for Audit Team",
		"fieldtype": "Small Text",
		"insert_after": "custom_service_priority",
	},
]

CUSTOMER_RECORD_TABLE_FIELDS = [
	{
		"fieldname": "custom_ownership_tab",
		"label": "Ownership and Governance",
		"fieldtype": "Tab Break",
		"insert_after": "custom_special_attention",
	},
	{
		"fieldname": "custom_shareholders",
		"label": "Shareholders",
		"fieldtype": "Table",
		"options": "Client Shareholder",
		"insert_after": "custom_ownership_tab",
	},
	{
		"fieldname": "custom_beneficial_owners",
		"label": "Beneficial Owners",
		"fieldtype": "Table",
		"options": "Client Beneficial Owner",
		"insert_after": "custom_shareholders",
	},
	{
		"fieldname": "custom_board_members",
		"label": "Board Members",
		"fieldtype": "Table",
		"options": "Client Board Member",
		"insert_after": "custom_beneficial_owners",
	},
	{
		"fieldname": "custom_tax_compliance_tab",
		"label": "Tax and Compliance",
		"fieldtype": "Tab Break",
		"insert_after": "custom_board_members",
	},
	{
		"fieldname": "custom_tax_registrations",
		"label": "Tax Registrations",
		"fieldtype": "Table",
		"options": "Client Tax Registration",
		"insert_after": "custom_tax_compliance_tab",
	},
	{
		"fieldname": "custom_compliance_certificates",
		"label": "Compliance Documents",
		"fieldtype": "Table",
		"options": "Compliance Certificate",
		"insert_after": "custom_tax_registrations",
	},
	{
		"fieldname": "custom_banking_tab",
		"label": "Banking",
		"fieldtype": "Tab Break",
		"insert_after": "custom_compliance_certificates",
	},
	{
		"fieldname": "custom_bank_accounts",
		"label": "Bank Accounts",
		"fieldtype": "Table",
		"options": "Client Bank Account",
		"insert_after": "custom_banking_tab",
	},
	{
		"fieldname": "custom_budgets_tab",
		"label": "Budgets",
		"fieldtype": "Tab Break",
		"insert_after": "custom_bank_accounts",
	},
	{
		"fieldname": "custom_budget_lines",
		"label": "Budget Lines",
		"fieldtype": "Table",
		"options": "Client Budget Line",
		"insert_after": "custom_budgets_tab",
	},
]

QUOTATION_CUSTOM_FIELDS = [
	{
		"fieldname": "custom_customer_tax_id",
		"label": "Customer Tax ID",
		"fieldtype": "Data",
		"insert_after": "customer_name",
		"read_only": 1,
		"print_hide": 0,
		"depends_on": "eval:doc.quotation_to == 'Customer'",
	}
]

CUSTOMER_TYPE_OPTIONS = (
	"Company",
	"Individual",
	"Partnership",
	"Enterprise",
	"Foreign Branch",
	"Cooperative",
	"NGO",
	"Faith Based Organisation",
	"Foundation/Trust",
	"JV",
	"AOP",
	"SPV",
	"Representative Office",
)


def _sync_customer_type_options():
	filters = {
		"doc_type": "Customer",
		"doctype_or_field": "DocField",
		"field_name": "customer_type",
		"property": "options",
	}
	options = "\n".join(CUSTOMER_TYPE_OPTIONS)
	property_setter = frappe.db.get_value("Property Setter", filters, "name")
	if property_setter:
		frappe.db.set_value("Property Setter", property_setter, "value", options)
	else:
		frappe.make_property_setter(
			{
				"doctype": "Customer",
				"doctype_or_field": "DocField",
				"fieldname": "customer_type",
				"property": "options",
				"value": options,
				"property_type": "Text",
			}
		)


def setup():
	create_custom_fields(
		{
			"Customer": CUSTOMER_CUSTOM_FIELDS,
			"Quotation": QUOTATION_CUSTOM_FIELDS,
		}
	)
	_sync_customer_type_options()
	frappe.clear_cache(doctype="Customer")
	frappe.clear_cache(doctype="Quotation")
	if all(
		frappe.db.exists("DocType", doctype) and frappe.get_meta(doctype).istable
		for doctype in CUSTOMER_TABLE_DOCTYPES
	):
		setup_customer_record_tables()


CUSTOMER_TABLE_DOCTYPES = tuple(
	field["options"] for field in CUSTOMER_RECORD_TABLE_FIELDS if field["fieldtype"] == "Table"
)


def setup_customer_record_tables():
	create_custom_fields({"Customer": CUSTOMER_RECORD_TABLE_FIELDS})
	frappe.clear_cache(doctype="Customer")
