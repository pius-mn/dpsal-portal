import frappe
from frappe import _


STRUCTURE_TAXONOMY = {
	"Individual": {"sub1": [], "sub2": [], "sub3": [], "law": "", "authority": "RRA"},
	"Enterprise": {"sub1": [], "sub2": [], "sub3": [], "law": "", "authority": "RDB"},
	"Partnership": {
		"sub1": [
			"General partnership (GP)",
			"Limited partnership (LP)",
			"Limited liability partnership (LLP)",
			"Foreign partnership (FP)",
			"Others",
		],
		"sub2": [],
		"sub3": [],
		"law": "008/2021 of 16/02/2021",
		"authority": "RDB",
	},
	"Company": {
		"sub1": ["Private", "Public"],
		"sub2": [
			"Company Limited by Shares",
			"Company Limited by Guarantee",
			"Company Limited by Shares and Guarantee",
			"Unlimited Company",
			"Protected cell company",
		],
		"sub3": [
			"Subsidiary",
			"Holding",
			"Wholly owned Subsidiary",
			"Virtually wholly owned subsidiary",
			"One person company",
		],
		"law": "007/2021 of 05/02/2021",
		"authority": "RDB",
	},
	"Foreign Branch": {
		"sub1": [],
		"sub2": [],
		"sub3": [],
		"law": "007/2021 of 05/02/2021",
		"authority": "RDB",
	},
	"Cooperative": {
		"sub1": [
			"Agriculture cooperative",
			"Livestock cooperative",
			"Fishing cooperative",
			"Production and agro-processing cooperative",
			"Financial service cooperative",
			"Traders' cooperative",
			"Consumers' cooperative",
			"People and goods transportation cooperative",
			"Handicraft cooperative",
			"Mining, quarrying, mines and gas extraction cooperative",
			"Construction cooperative",
			"Service cooperative",
			"Multipurpose cooperative",
			"Others",
		],
		"sub2": [],
		"sub3": [],
		"law": "057/2024 of 20/06/2024",
		"authority": "RCA",
	},
	"NGO": {
		"sub1": ["National", "International"],
		"sub2": [
			"Specific Community Interest based",
			"General Community Interest based",
			"Members' Interest based",
			"Profession interest based",
			"Sport Promotion based",
			"Umbrella",
			"Forum of umbrellas",
		],
		"sub3": [],
		"law": "058/2024 of 20/06/2024",
		"authority": "RGB",
	},
	"Faith Based Organisation": {
		"sub1": ["Organisation", "Ministry", "Umbrella", "Forum of umbrellas"],
		"sub2": [],
		"sub3": [],
		"law": "72/2018",
		"authority": "RGB",
	},
	"Foundation/Trust": {
		"sub1": [
			"Private-benefit foundation",
			"Common-benefit foundation",
			"Mixed-benefit foundation",
		],
		"sub2": [],
		"sub3": [],
		"law": "059/2021 of 14/10/2021",
		"authority": "RGB",
	},
	"JV": {
		"sub1": ["National", "International"],
		"sub2": [],
		"sub3": [],
		"law": "007/2021 of 05/02/2021",
		"authority": "",
	},
	"AOP": {"sub1": [], "sub2": [], "sub3": [], "law": "", "authority": "Notary"},
	"SPV": {"sub1": [], "sub2": [], "sub3": [], "law": "", "authority": ""},
	"Representative Office": {
		"sub1": [],
		"sub2": [],
		"sub3": [],
		"law": "",
		"authority": "RRA",
	},
}

SUBCATEGORY_FIELDS = (
	("custom_structure_subcategory", "sub1"),
	("custom_structure_subcategory_2", "sub2"),
	("custom_structure_subcategory_3", "sub3"),
)

DEFAULT_DOCUMENT_SET = [
	("Certificate of incorporation", "Statutory", 0),
	("Registration certificate", "Statutory", 0),
	("Full details", "Statutory", 0),
	("VAT certificate", "Statutory", 0),
	("TIN certificate", "Statutory", 0),
	("Trading licence", "Licence", 1),
	("Memorandum of Association", "Statutory", 0),
	("Articles of Association", "Statutory", 0),
	("Share certificates", "Statutory", 0),
	("Shareholder resolutions - all", "Statutory", 0),
	("Board resolutions", "Statutory", 0),
	("Shareholders' passports/IDs & visas", "ID/Passport", 1),
	("Board of Directors' passports/IDs & visas", "ID/Passport", 1),
	("Management personnel passports/IDs & visas", "ID/Passport", 1),
	("KYC - annual", "KYC", 1),
	("Criminal record certificates - shareholders & management", "Report", 1),
	("Tax Clearance Certificate (TCC)", "Report", 1),
	("RSSB clearance certificate", "Report", 1),
	("Good standing / non-bankruptcy (RDB)", "Report", 1),
	("Exemption certificates", "Statutory", 1),
	("Licenses - if any", "Licence", 1),
	("CRB report", "Report", 1),
	("Academic qualification certificates", "Report", 0),
	("CVs - shareholders, board, managers", "Report", 0),
	("Disclosure by Board members - conflict of interest", "Report", 0),
	("Director appointment contract/letter", "Contract", 0),
	("Employee disclosures", "Report", 0),
	("List of employees & representatives", "Report", 0),
	("Company profile", "Other", 0),
	("Business plan", "Other", 0),
	("Budget / operational expense budget", "Other", 0),
	("Fixed assets register", "Other", 0),
	("HR policies", "Other", 0),
	("Accounting policies", "Other", 0),
	("ICT policies", "Other", 0),
	("Contracts - all (employment, rental, clearing agent, consultant, auditor)", "Contract", 0),
]

STRUCTURE_EXTRA_DOCUMENTS = {
	"Company": [("Shareholders' list (updated)", "Report", 0)],
	"Cooperative": [
		("Membership certificate(s)", "Report", 0),
		("Cooperative general assembly minutes", "Report", 0),
	],
	"NGO": [
		("RGB registration certificate", "Statutory", 0),
		("Board appointment letters", "Contract", 0),
	],
	"Foundation/Trust": [
		("Trust deed", "Statutory", 0),
		("RGB registration certificate", "Statutory", 0),
	],
	"Partnership": [("Partnership deed", "Statutory", 0)],
	"Foreign Branch": [
		("Parent company registration certificate", "Statutory", 0),
		("Parent company resolution + MoA (used to register in Rwanda)", "Statutory", 0),
	],
	"Faith Based Organisation": [
		("RGB registration certificate", "Statutory", 0),
		("Founding statute / constitution", "Statutory", 0),
	],
}


def structure_defaults(legal_structure_type, structure_subcategory=None):
	spec = STRUCTURE_TAXONOMY.get(legal_structure_type) or {}
	law = spec.get("law") or ""
	if legal_structure_type == "JV":
		law = {
			"National": "Contract-based (no specific law)",
			"International": "007/2021 of 05/02/2021",
		}.get(structure_subcategory, "")
	return {"law": law, "authority": spec.get("authority") or ""}


def validate_structure_subcategories(legal_structure_type, **subcategories):
	if not legal_structure_type:
		return None
	spec = STRUCTURE_TAXONOMY.get(legal_structure_type) or {}
	for fieldname, key in SUBCATEGORY_FIELDS:
		value = subcategories.get(fieldname)
		if not value:
			continue
		options = spec.get(key) or []
		if (
			legal_structure_type == "NGO"
			and key == "sub2"
			and subcategories.get("custom_structure_subcategory") == "International"
		):
			options = []
		if value not in options:
			return fieldname, value
	return None


def validate_customer_legal_structure(doc, method=None):
	legal_structure_type = doc.get("customer_type")
	invalid = validate_structure_subcategories(
		legal_structure_type,
		**{fieldname: doc.get(fieldname) for fieldname, _ in SUBCATEGORY_FIELDS},
	)
	if invalid:
		fieldname, value = invalid
		label = frappe.get_meta("Customer").get_label(fieldname) or fieldname
		frappe.throw(
			_('{0}: "{1}" is not valid for the legal structure "{2}".').format(
				label, value, legal_structure_type
			),
			frappe.ValidationError,
		)

	defaults = structure_defaults(
		legal_structure_type, doc.get("custom_structure_subcategory")
	)
	if not doc.get("custom_governing_law") and defaults["law"]:
		doc.custom_governing_law = defaults["law"]
	if not doc.get("custom_regulating_authority") and defaults["authority"]:
		doc.custom_regulating_authority = defaults["authority"]

	# Ensure any compliance document titles exist in Client Document Master
	if frappe.db.exists("DocType", "Client Document Master"):
		for row in doc.get("custom_compliance_certificates") or []:
			if row.document_title and not frappe.db.exists("Client Document Master", row.document_title):
				frappe.get_doc(
					{
						"doctype": "Client Document Master",
						"document_title": row.document_title,
						"doc_type": row.doc_type or "Other",
						"has_expiry": row.has_expiry or 0,
						"is_required": row.is_required if row.is_required is not None else 1,
						"issuing_authority": row.issuing_authority,
						"short_alias": row.short_alias,
					}
				).insert(ignore_permissions=True)


def default_document_rows(legal_structure_type=None):
	rows = [
		{
			"document_title": title,
			"doc_type": category,
			"is_required": 1,
			"has_expiry": has_expiry,
		}
		for title, category, has_expiry in DEFAULT_DOCUMENT_SET
	]
	for structure, extra in STRUCTURE_EXTRA_DOCUMENTS.items():
		if structure == legal_structure_type:
			rows.extend(
				{
					"document_title": title,
					"doc_type": category,
					"is_required": 1,
					"has_expiry": has_expiry,
				}
				for title, category, has_expiry in extra
			)
	return rows
