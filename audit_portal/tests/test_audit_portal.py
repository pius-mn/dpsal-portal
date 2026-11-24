import base64
import io
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.contacts.doctype.address.address import get_default_address
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file
from audit_portal.api.signup import submit_signup_request
from audit_portal.provisioning import (
	ensure_audit_client_role,
	ensure_audit_document_reviewer_role,
	ensure_default_document_masters,
	provision_client_for_signup_request,
)
from audit_portal.api.client_records import (
	get_client_records,
	save_customer_details,
	save_client_record,
	save_customer_linked_record,
	upload_compliance_file,
	add_default_compliance_requirements,
)
from audit_portal.api.portal import (
	get_current_customer,
	get_portal_data,
	get_quotations,
	get_quotation_details,
	get_invoices,
	action_quotation,
	get_invoice_pdf_url,
)
from audit_portal.legal_structure import (
	default_document_rows,
	structure_defaults,
	validate_structure_subcategories,
)
from audit_portal.customizations import CUSTOMER_TYPE_OPTIONS, setup as setup_customizations


class TestAuditPortal(FrappeTestCase):

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		ensure_default_document_masters()
		ensure_audit_client_role()
		ensure_default_document_masters()

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def get_valid_customer_group(self):
		return frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial"

	def get_valid_territory(self):
		return frappe.db.get_value("Territory", {"is_group": 0}, "name") or "Kenya"

	def get_or_create_company(self):
		company_name = frappe.db.get_single_value("Global Defaults", "default_company")
		if not company_name or not frappe.db.exists("Company", company_name):
			company_name = frappe.db.get_value("Company", {}, "name")
		return company_name

	def add_customer_child(self, customer_name, fieldname, values):
		customer = frappe.get_doc("Customer", customer_name)
		row = customer.append(fieldname, values)
		customer.save(ignore_permissions=True)
		return row

	def test_01_guest_signup_creates_pending_request_only(self):
		"""
		Ensure guest signup only creates a Pending Client Signup Request
		and never directly provisions Customer or User records.
		"""
		frappe.set_user("Guest")
		test_email = "guest_test_org@example.com"
		company = "Guest Test Org Ltd"

		# Clean up any residual data
		if frappe.db.exists("Client Signup Request", {"email": test_email}):
			frappe.db.delete("Client Signup Request", {"email": test_email})
		if frappe.db.exists("Customer", {"customer_name": company}):
			frappe.db.delete("Customer", {"customer_name": company})
		if frappe.db.exists("User", test_email):
			frappe.delete_doc("User", test_email, force=1)

		res = submit_signup_request(
			company_name=company,
			contact_name="Alice Guest",
			email=test_email,
			phone="+254711000111",
			notes="Initial compliance audit enquiry"
		)

		self.assertEqual(res["status"], "success")
		req_name = res["name"]

		# Verify staging request
		req_doc = frappe.get_doc("Client Signup Request", req_name)
		self.assertEqual(req_doc.approval_status, "Pending")
		self.assertIsNone(req_doc.customer)
		self.assertIsNone(req_doc.portal_user)

		# Crucial: Live Customer and User must NOT be created yet
		customer_exists = frappe.db.exists("Customer", {"customer_name": company})
		user_exists = frappe.db.exists("User", test_email)
		self.assertFalse(customer_exists, "Customer must not be created on guest signup")
		self.assertFalse(user_exists, "User must not be created on guest signup")

		# Duplicate email check
		with self.assertRaises(frappe.DuplicateEntryError):
			submit_signup_request(
				company_name="Duplicate Org",
				contact_name="Another Person",
				email=test_email
			)

	def test_02_admin_approval_and_idempotent_provisioning(self):
		"""
		Ensure non-admin cannot approve, and Admin approval atomically & idempotently
		provisions Customer, User with Audit Client role, and User Permission.
		"""
		test_email = "provision_test@example.com"
		company = "Provision Test Co"

		# Cleanup
		if frappe.db.exists("Client Signup Request", {"email": test_email}):
			frappe.db.delete("Client Signup Request", {"email": test_email})
		if frappe.db.exists("Customer", {"customer_name": company}):
			frappe.db.delete("Customer", {"customer_name": company})
		if frappe.db.exists("User", test_email):
			frappe.delete_doc("User", test_email, force=1)

		req = frappe.get_doc({
			"doctype": "Client Signup Request",
			"company_name": company,
			"contact_name": "Bob Partner",
			"email": test_email,
			"phone": "+254722000222",
			"approval_status": "Pending"
		}).insert(ignore_permissions=True)

		# 1. Non-admin user cannot transition to Approved
		dummy_user_email = "regular_staff_tester@example.com"
		if not frappe.db.exists("User", dummy_user_email):
			dummy_user = frappe.get_doc({
				"doctype": "User",
				"email": dummy_user_email,
				"first_name": "Regular",
				"user_type": "System User",
				"roles": [{"role": "All"}]
			}).insert(ignore_permissions=True)

		frappe.set_user(dummy_user_email)
		req_test = frappe.get_doc("Client Signup Request", req.name)
		req_test.approval_status = "Approved"
		with self.assertRaises(frappe.PermissionError):
			req_test.save()

		# 2. Administrator approves
		frappe.set_user("Administrator")
		req_admin = frappe.get_doc("Client Signup Request", req.name)
		req_admin.approval_status = "Approved"
		req_admin.save()

		# Verify Customer provisioned
		self.assertTrue(frappe.db.exists("Customer", {"customer_name": company}))
		customer_name = frappe.db.get_value("Customer", {"customer_name": company}, "name")

		# Verify User provisioned with Audit Client role
		self.assertTrue(frappe.db.exists("User", test_email))
		user_doc = frappe.get_doc("User", test_email)
		self.assertEqual(user_doc.user_type, "Website User")
		roles = [r.role for r in user_doc.roles]
		self.assertIn("Audit Client", roles)

		# Verify User Permission provisioned
		perm_exists = frappe.db.exists("User Permission", {
			"user": test_email,
			"allow": "Customer",
			"for_value": customer_name
		})
		self.assertTrue(perm_exists, "User Permission for Customer was not provisioned")

		# Verify linked back onto Client Signup Request
		req_reloaded = frappe.get_doc("Client Signup Request", req.name)
		self.assertEqual(req_reloaded.customer, customer_name)
		self.assertEqual(req_reloaded.portal_user, test_email)
		self.assertFalse(frappe.db.exists("DocType", "Client Profile"))

		# 3. Test Idempotency: re-running provisioning does not duplicate or error
		result = provision_client_for_signup_request(req_reloaded)
		self.assertEqual(result["customer"], customer_name)
		self.assertEqual(result["portal_user"], test_email)

		# Count permissions
		perm_count = frappe.db.count("User Permission", {
			"user": test_email,
			"allow": "Customer",
			"for_value": customer_name
		})
		self.assertEqual(perm_count, 1, "User Permission was duplicated")

	def test_03_cross_customer_isolation(self):
		"""
		Strict row-level scoping test:
		Customer A and Customer B both have compliance items, quotations, and invoices.
		User A must NEVER read or mutate Customer B's records.
		"""
		valid_cg = self.get_valid_customer_group()
		valid_terr = self.get_valid_territory()
		company = self.get_or_create_company()

		# Setup Customer A
		cust_a_name = "Customer Alpha Isolation Ltd"
		email_a = "alpha_client_user@example.com"
		if not frappe.db.exists("Customer", {"customer_name": cust_a_name}):
			cust_a = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": cust_a_name,
				"customer_type": "Company",
				"customer_group": valid_cg,
				"territory": valid_terr
			}).insert(ignore_permissions=True)
		else:
			cust_a = frappe.get_doc("Customer", {"customer_name": cust_a_name})

		if not frappe.db.exists("User", email_a):
			user_a = frappe.get_doc({
				"doctype": "User",
				"email": email_a,
				"first_name": "Alpha User",
				"user_type": "Website User",
				"roles": [{"role": "Audit Client"}]
			}).insert(ignore_permissions=True)

		# Ensure User Permission for Alpha
		if not frappe.db.exists("User Permission", {"user": email_a, "allow": "Customer", "for_value": cust_a.name}):
			frappe.get_doc({
				"doctype": "User Permission",
				"user": email_a,
				"allow": "Customer",
				"for_value": cust_a.name,
				"apply_to_all_doctypes": 1
			}).insert(ignore_permissions=True)

		# Setup Customer B
		cust_b_name = "Customer Beta Isolation Ltd"
		email_b = "beta_client_user@example.com"
		if not frappe.db.exists("Customer", {"customer_name": cust_b_name}):
			cust_b = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": cust_b_name,
				"customer_type": "Company",
				"customer_group": valid_cg,
				"territory": valid_terr
			}).insert(ignore_permissions=True)
		else:
			cust_b = frappe.get_doc("Customer", {"customer_name": cust_b_name})

		if not frappe.db.exists("User", email_b):
			user_b = frappe.get_doc({
				"doctype": "User",
				"email": email_b,
				"first_name": "Beta User",
				"user_type": "Website User",
				"roles": [{"role": "Audit Client"}]
			}).insert(ignore_permissions=True)

		# Ensure User Permission for Beta
		if not frappe.db.exists("User Permission", {"user": email_b, "allow": "Customer", "for_value": cust_b.name}):
			frappe.get_doc({
				"doctype": "User Permission",
				"user": email_b,
				"allow": "Customer",
				"for_value": cust_b.name,
				"apply_to_all_doctypes": 1
			}).insert(ignore_permissions=True)

		# Ensure item for quotation and invoice exists
		test_item_code = "Audit Consultation Service"
		if not frappe.db.exists("Item", test_item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": test_item_code,
				"item_group": "Services",
				"is_stock_item": 0
			}).insert(ignore_permissions=True)

		# Create Quotation for Alpha
		q_a = frappe.get_doc({
			"doctype": "Quotation",
			"quotation_to": "Customer",
			"party_name": cust_a.name,
			"transaction_date": frappe.utils.nowdate(),
			"items": [{
				"item_code": test_item_code,
				"qty": 1,
				"rate": 15000
			}]
		}).insert(ignore_permissions=True)
		q_a.submit()

		# Create Quotation for Beta
		q_b = frappe.get_doc({
			"doctype": "Quotation",
			"quotation_to": "Customer",
			"party_name": cust_b.name,
			"transaction_date": frappe.utils.nowdate(),
			"items": [{
				"item_code": test_item_code,
				"qty": 1,
				"rate": 30000
			}]
		}).insert(ignore_permissions=True)
		q_b.submit()

		# Create Sales Invoice for Alpha
		inv_a = frappe.get_doc({
			"doctype": "Sales Invoice",
			"customer": cust_a.name,
			"company": company,
			"posting_date": frappe.utils.nowdate(),
			"due_date": frappe.utils.add_days(frappe.utils.nowdate(), 14),
			"items": [{
				"item_code": test_item_code,
				"qty": 1,
				"rate": 15000
			}]
		}).insert(ignore_permissions=True)
		inv_a.submit()

		# Create Sales Invoice for Beta
		inv_b = frappe.get_doc({
			"doctype": "Sales Invoice",
			"customer": cust_b.name,
			"company": company,
			"posting_date": frappe.utils.nowdate(),
			"due_date": frappe.utils.add_days(frappe.utils.nowdate(), 14),
			"items": [{
				"item_code": test_item_code,
				"qty": 1,
				"rate": 30000
			}]
		}).insert(ignore_permissions=True)
		inv_b.submit()

		alpha_requirement = self.add_customer_child(
			cust_a.name,
			"custom_compliance_certificates",
			{
				"document_title": "Certificate of incorporation",
				"doc_type": "Statutory",
				"is_required": 1,
			},
		)
		beta_requirement = self.add_customer_child(
			cust_b.name,
			"custom_compliance_certificates",
			{
				"document_title": "Certificate of incorporation",
				"doc_type": "Statutory",
				"is_required": 1,
			},
		)

		# --- TEST AS USER ALPHA ---
		frappe.set_user(email_a)

		# 1. Resolved customer must be Alpha
		resolved = get_current_customer()
		self.assertEqual(resolved, cust_a.name)
		upload = io.BytesIO(
			base64.b64decode(
				"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/r9sAAAAASUVORK5CYII="
			)
		)
		upload.filename = "incorporation.png"
		with patch(
			"audit_portal.api.client_records.frappe.request",
			SimpleNamespace(files={"file": upload}),
		):
			upload_result = upload_compliance_file(alpha_requirement.name)
		self.assertEqual(upload_result["status"], "Pending Review")
		self.assertTrue(
			frappe.db.exists(
				"Client Verification Request",
				{
					"name": upload_result["name"],
					"customer": cust_a.name,
					"compliance_requirement": alpha_requirement.name,
				},
			)
		)
		self.assertEqual(
			frappe.db.get_value(
				"Compliance Certificate",
				alpha_requirement.name,
				"verification_request",
			),
			upload_result["name"],
		)
		portal_data = get_portal_data()
		self.assertNotIn("compliance_items", portal_data)
		self.assertNotIn("compliance_summary", portal_data)

		details_result = save_customer_details({
			"customer_type": "Partnership",
			"structure_subcategory": "General partnership (GP)",
			"registration_no": "ALPHA-REG-01",
			"tax_id": "ALPHA-TIN-01",
			"customer": cust_b.name,
			"risk_nationality": "Red",
		})
		alpha_customer = frappe.get_doc("Customer", details_result["name"])
		self.assertEqual(alpha_customer.name, cust_a.name)
		self.assertEqual(alpha_customer.customer_type, "Partnership")
		self.assertEqual(alpha_customer.custom_registration_no, "ALPHA-REG-01")
		self.assertEqual(alpha_customer.custom_governing_law, "008/2021 of 16/02/2021")
		self.assertEqual(alpha_customer.custom_regulating_authority, "RDB")
		self.assertFalse(alpha_customer.custom_risk_nationality)
		self.assertFalse(frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": "custom_legal_structure_type"}))
		customer_field_order = [field.fieldname for field in frappe.get_meta("Customer").fields]
		self.assertLess(
			customer_field_order.index("custom_audit_profile_section"),
			customer_field_order.index("custom_structure_subcategory"),
		)
		self.assertLess(
			customer_field_order.index("custom_structure_subcategory"),
			customer_field_order.index("custom_special_attention"),
		)
		self.assertEqual(
			frappe.get_meta("Customer").get_field("custom_structure_subcategory").fieldtype,
			"Select",
		)
		self.assertTrue(frappe.get_meta("Customer").has_field("custom_structure_subcategory_2"))
		self.assertTrue(frappe.get_meta("Customer").has_field("custom_structure_subcategory_3"))
		self.assertEqual(frappe.db.get_value("Customer", cust_a.name, "tax_id"), "ALPHA-TIN-01")
		self.assertEqual(get_client_records()["customer_details"]["tax_id"], "ALPHA-TIN-01")
		self.assertIn("Subsidiary", get_client_records()["legal_structure_config"]["Company"]["sub3"])
		self.assertIn("Partnership", get_client_records()["customer_types"])
		self.assertIn("NGO", get_client_records()["customer_types"])
		self.assertEqual(get_client_records()["customer_details"]["customer_type"], "Partnership")
		self.assertEqual(get_client_records()["customer_details"]["registration_no"], "ALPHA-REG-01")
		self.assertFalse(frappe.db.exists("DocType", "Client Profile"))
		with self.assertRaises(frappe.ValidationError):
			save_customer_details({"customer_type": "Unknown Legal Form"})
		with self.assertRaises(frappe.ValidationError):
			save_customer_details({
				"customer_type": "Company",
				"structure_subcategory": "General partnership (GP)",
			})
		with self.assertRaises(frappe.ValidationError):
			save_customer_details({
				"customer_type": "NGO",
				"structure_subcategory": "International",
				"structure_subcategory_2": "Specific Community Interest based",
			})
		save_customer_details({"customer_type": "NGO", "structure_subcategory": "National"})
		self.assertEqual(frappe.db.get_value("Customer", cust_a.name, "customer_type"), "NGO")
		save_customer_details({"tin": "ALPHA-TIN-LEGACY"})
		self.assertEqual(frappe.db.get_value("Customer", cust_a.name, "tax_id"), "ALPHA-TIN-LEGACY")
		self.assertEqual(get_client_records()["customer_details"]["tax_id"], "ALPHA-TIN-LEGACY")

		alpha_shareholder = save_client_record(
			doctype="Client Shareholder",
			values={"member_name": "Alpha Shareholder", "share_pct": 45, "customer": cust_b.name},
		)
		self.assertEqual(
			frappe.db.get_value("Client Shareholder", alpha_shareholder["name"], "parent"),
			cust_a.name,
		)
		alpha_tax_registration = save_client_record(
			doctype="Client Tax Registration",
			values={"tax_type": "Value Added Tax", "frequency": "Monthly", "due_date": frappe.utils.add_days(frappe.utils.nowdate(), 30)},
		)
		alpha_bank = save_client_record(
			doctype="Client Bank Account",
			values={
				"bank_name": "Alpha Bank",
				"account_number": "000123456",
				"account_type": "Current",
				"customer": cust_b.name,
			},
		)
		alpha_budget = save_client_record(
			doctype="Client Budget Line",
			values={
				"budget_line": "Office operations",
				"budget_period": "FY2026",
				"annual_budget": 120000,
				"actual_spend": 42000,
			},
		)
		save_client_record(
			doctype="Client Bank Account",
			name=alpha_bank["name"],
			values={"branch_name": "Alpha Main Branch"},
		)
		save_client_record(
			doctype="Client Budget Line",
			name=alpha_budget["name"],
			values={"actual_spend": 45000},
		)
		self.assertEqual(frappe.db.get_value("Client Bank Account", alpha_bank["name"], "parent"), cust_a.name)
		self.assertEqual(frappe.db.get_value("Client Bank Account", alpha_bank["name"], "branch_name"), "Alpha Main Branch")
		self.assertEqual(frappe.db.get_value("Client Budget Line", alpha_budget["name"], "parent"), cust_a.name)
		self.assertEqual(frappe.db.get_value("Client Budget Line", alpha_budget["name"], "actual_spend"), 45000)
		with self.assertRaises(frappe.ValidationError):
			save_client_record(
				doctype="Client Budget Line",
				values={"budget_line": "Invalid currency", "currency": "Currency That Does Not Exist"},
			)
		country = frappe.db.get_value("Country", {}, "name")
		alpha_contact = save_customer_linked_record(
			doctype="Contact",
			values={
				"first_name": "Alpha",
				"last_name": "Contact",
				"email": "alpha.contact@example.com",
				"phone": "+250700000001",
			},
		)
		alpha_address = save_customer_linked_record(
			doctype="Address",
			values={
				"address_title": "Alpha Main Office",
				"address_type": "Office",
				"address_line1": "1 Alpha Street",
				"city": "Kigali",
				"country": country,
			},
		)
		self.assertTrue(frappe.db.get_value("Address", alpha_address["name"], "is_primary_address"))
		self.assertEqual(
			frappe.db.get_value("Customer", cust_a.name, "customer_primary_address"),
			alpha_address["name"],
		)
		self.assertEqual(get_default_address("Customer", cust_a.name), alpha_address["name"])
		self.assertEqual(
			frappe.db.get_value("Client Tax Registration", alpha_tax_registration["name"], "parent"),
			cust_a.name,
		)
		with self.assertRaises(frappe.ValidationError):
			save_client_record(
				doctype="Client Shareholder",
				values={"member_name": "Invalid Shareholder", "share_pct": 101},
			)

		frappe.set_user(email_b)
		beta_shareholder = save_client_record(
			doctype="Client Shareholder",
			values={"member_name": "Beta Shareholder", "share_pct": 100},
		)
		beta_tax_registration = save_client_record(
			doctype="Client Tax Registration",
			values={"tax_type": "Corporate Income Tax", "frequency": "Annually"},
		)
		beta_bank = save_client_record(
			doctype="Client Bank Account",
			values={"bank_name": "Beta Bank", "account_number": "999654321"},
		)
		beta_budget = save_client_record(
			doctype="Client Budget Line",
			values={"budget_line": "Beta operations", "annual_budget": 50000},
		)
		beta_contact = save_customer_linked_record(
			doctype="Contact",
			values={"first_name": "Beta", "email": "beta.contact@example.com"},
		)
		beta_address = save_customer_linked_record(
			doctype="Address",
			values={
				"address_title": "Beta Main Office",
				"address_type": "Office",
				"address_line1": "2 Beta Street",
				"city": "Kigali",
				"country": country,
			},
		)
		frappe.set_user(email_a)
		client_records = get_client_records()
		self.assertEqual(client_records["customer_details"]["registration_no"], "ALPHA-REG-01")
		alpha_shareholder_names = [row.name for row in client_records["records"]["Client Shareholder"]]
		self.assertIn(alpha_shareholder["name"], alpha_shareholder_names)
		self.assertNotIn(beta_shareholder["name"], alpha_shareholder_names)
		alpha_tax_names = [row.name for row in client_records["records"]["Client Tax Registration"]]
		self.assertIn(alpha_tax_registration["name"], alpha_tax_names)
		self.assertNotIn(beta_tax_registration["name"], alpha_tax_names)
		for doctype, alpha_record, beta_record in (
			("Client Bank Account", alpha_bank, beta_bank),
			("Client Budget Line", alpha_budget, beta_budget),
		):
			record_names = [row.name for row in client_records["records"][doctype]]
			self.assertIn(alpha_record["name"], record_names)
			self.assertNotIn(beta_record["name"], record_names)
			with self.assertRaises(frappe.PermissionError):
				save_client_record(
					doctype=doctype,
					name=beta_record["name"],
					values={},
				)
		alpha_contact_names = [row["name"] for row in client_records["contacts"]]
		self.assertIn(alpha_contact["name"], alpha_contact_names)
		self.assertNotIn(beta_contact["name"], alpha_contact_names)
		alpha_address_names = [row["name"] for row in client_records["addresses"]]
		self.assertIn(alpha_address["name"], alpha_address_names)
		self.assertNotIn(beta_address["name"], alpha_address_names)
		self.assertIn(country, client_records["countries"])
		client_document_names = [
			row["name"] for row in client_records["records"]["Compliance Certificate"]
		]
		self.assertIn(alpha_requirement.name, client_document_names)
		self.assertNotIn(beta_requirement.name, client_document_names)
		with self.assertRaises(frappe.PermissionError):
			save_client_record(
				doctype="Compliance Certificate",
				values={"document_title": "Client-created document"},
			)
		with self.assertRaises(frappe.PermissionError):
			upload_compliance_file(beta_requirement.name)
		with self.assertRaises(frappe.PermissionError):
			save_client_record(
				doctype="Client Shareholder",
				name=beta_shareholder["name"],
				values={"member_name": "Attempted cross-customer edit"},
			)
		with self.assertRaises(frappe.PermissionError):
			save_customer_linked_record(
				doctype="Contact",
				name=beta_contact["name"],
				values={"first_name": "Unauthorized"},
			)
		with self.assertRaises(frappe.PermissionError):
			save_customer_linked_record(
				doctype="Address",
				name=beta_address["name"],
				values={"city": "Unauthorized"},
			)
		with self.assertRaises(frappe.PermissionError):
			save_client_record(doctype="Customer", values={"customer_name": "Unscoped write"})

		# 2. Quotations read test
		alpha_quotes = get_quotations()
		alpha_q_names = [q.name for q in alpha_quotes]
		self.assertIn(q_a.name, alpha_q_names)
		self.assertNotIn(q_b.name, alpha_q_names, "Customer A must never see Customer B's quotations")
		alpha_quote_details = get_quotation_details(quotation_name=q_a.name)
		self.assertEqual(alpha_quote_details["name"], q_a.name)
		with self.assertRaises(frappe.PermissionError):
			get_quotation_details(quotation_name=q_b.name)

		# 3. Invoices read test
		alpha_invoices = get_invoices()
		alpha_inv_names = [inv.name for inv in alpha_invoices]
		self.assertIn(inv_a.name, alpha_inv_names)
		self.assertNotIn(inv_b.name, alpha_inv_names, "Customer A must never see Customer B's invoices")

		# 4. Cross-customer mutation test: User Alpha tries to act on User Beta's quotation
		with self.assertRaises(frappe.PermissionError):
			action_quotation(quotation_name=q_b.name, action="accept")

		with self.assertRaises(frappe.PermissionError):
			action_quotation(quotation_name=q_b.name, action="reject")

		# 5. Cross-customer download test: User Alpha tries to download User Beta's invoice PDF
		with self.assertRaises(frappe.PermissionError):
			get_invoice_pdf_url(invoice_name=inv_b.name)

		# User Alpha can download their own invoice PDF
		pdf_res = get_invoice_pdf_url(invoice_name=inv_a.name)
		self.assertEqual(pdf_res["status"], "success")
		self.assertIn(inv_a.name, pdf_res["pdf_url"])

		# 6. User Alpha accepts their OWN quotation
		accept_res = action_quotation(quotation_name=q_a.name, action="accept")
		self.assertEqual(accept_res["status"], "success")
		self.assertEqual(accept_res["new_status"], "Replied")

		# A customer response is recorded as Replied. Ordered is reserved for quotations
		# with a linked Sales Order in ERPNext.
		q_a_updated = frappe.get_doc("Quotation", q_a.name)
		self.assertEqual(q_a_updated.status, "Replied")
		with self.assertRaises(frappe.ValidationError):
			action_quotation(quotation_name=q_a.name, action="accept")

		ambiguous_permission = frappe.get_doc({
			"doctype": "User Permission",
			"user": email_a,
			"allow": "Customer",
			"for_value": cust_b.name,
			"apply_to_all_doctypes": 1,
		}).insert(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			get_current_customer()
		frappe.set_user("Administrator")
		frappe.delete_doc("User Permission", ambiguous_permission.name, force=1)

	def test_04_unauthenticated_and_unmapped_access_denied(self):
		"""
		Ensure guest and unmapped users are strictly rejected with PermissionError.
		"""
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			get_current_customer()

		with self.assertRaises(frappe.PermissionError):
			get_portal_data()

		with self.assertRaises(frappe.PermissionError):
			get_quotations()

		with self.assertRaises(frappe.PermissionError):
			get_invoices()

	def test_05_document_review_requires_assigned_role_and_uses_desk(self):
		"""
		Verify that the perm-level-1 Review section on Client Verification Request
		enforces role access and that the before_save controller mirrors the
		decision to the linked Compliance Certificate child row.
		"""
		ensure_audit_document_reviewer_role()

		client_email = "staff_workspace_client@example.com"
		if not frappe.db.exists("User", client_email):
			frappe.get_doc({
				"doctype": "User",
				"email": client_email,
				"first_name": "Portal Client",
				"user_type": "Website User",
				"roles": [{"role": "Audit Client"}]
			}).insert(ignore_permissions=True)

		# Audit Client must not read CVR or Compliance Certificate
		frappe.set_user(client_email)
		self.assertFalse(frappe.has_permission("Compliance Certificate", "read"))
		self.assertFalse(frappe.has_permission("Compliance Certificate", "create"))
		self.assertFalse(frappe.has_permission("Client Verification Request", "read"))

		frappe.set_user("Administrator")
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "Team Workspace Test Customer",
			"customer_type": "Company",
			"customer_group": self.get_valid_customer_group(),
			"territory": self.get_valid_territory()
		}).insert(ignore_permissions=True)

		requirement = self.add_customer_child(
			customer.name,
			"custom_compliance_certificates",
			{
				"document_title": "Certificate of incorporation",
				"doc_type": "Statutory",
				"is_required": 1,
				"has_expiry": 1,
			},
		)
		self.assertEqual(requirement.status, "Not Submitted")
		self.assertTrue(requirement.is_required)
		self.assertTrue(requirement.has_expiry)

		certificate = self.add_customer_child(
			customer.name,
			"custom_compliance_certificates",
			{
				"document_title": "Certificate of incorporation",
				"attachment": "/private/files/incorporation-test.pdf",
				"status": "Pending Review",
				"is_required": 1,
			},
		)
		request = frappe.get_doc(
			{
				"doctype": "Client Verification Request",
				"customer": customer.name,
				"compliance_requirement": certificate.name,
				"document_title": certificate.document_title,
				"status": "Pending Review",
				"attachment": certificate.attachment,
				"submitted_by": "Administrator",
				"submitted_on": frappe.utils.now_datetime(),
			}
		).insert(ignore_permissions=True)
		customer_doc = frappe.get_doc("Customer", customer.name)
		row = next(
			row
			for row in customer_doc.custom_compliance_certificates
			if row.name == certificate.name
		)
		row.verification_request = request.name
		customer_doc.save(ignore_permissions=True)

		# Rejected without a reason must fail validation (before_save guard)
		req_doc = frappe.get_doc("Client Verification Request", request.name)
		req_doc.status = "Rejected"
		req_doc.rejection_reason = ""
		with self.assertRaises(frappe.ValidationError):
			req_doc.save(ignore_permissions=True)

		# Audit Client must not write perm-level-1 fields (no write on CVR)
		frappe.set_user(client_email)
		self.assertFalse(frappe.has_permission("Client Verification Request", "write"))

		# Provision the reviewer user
		reviewer_email = "audit_document_reviewer@example.com"
		frappe.set_user("Administrator")
		if not frappe.db.exists("User", reviewer_email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": reviewer_email,
					"first_name": "Document Reviewer",
					"user_type": "System User",
					"roles": [{"role": "Audit Document Reviewer"}],
				}
			).insert(ignore_permissions=True)
		else:
			reviewer = frappe.get_doc("User", reviewer_email)
			if "Audit Document Reviewer" not in [row.role for row in reviewer.roles]:
				reviewer.append("roles", {"role": "Audit Document Reviewer"})
				reviewer.save(ignore_permissions=True)

		# Reviewer can read and write (perm-level 0 read + perm-level 1 write)
		frappe.set_user(reviewer_email)
		self.assertTrue(frappe.has_permission("Client Verification Request", "read"))
		self.assertTrue(frappe.has_permission("Client Verification Request", "write"))

		# Reviewer sets status + reason via standard Desk save → before_save fires
		req_doc = frappe.get_doc("Client Verification Request", request.name)
		req_doc.status = "Rejected"
		req_doc.rejection_reason = "Upload a clearer copy."
		req_doc.save()

		self.assertEqual(req_doc.status, "Rejected")
		self.assertEqual(
			frappe.db.get_value("Client Verification Request", request.name, "status"),
			"Rejected",
		)
		self.assertEqual(
			frappe.db.get_value("Compliance Certificate", certificate.name, "rejection_reason"),
			"Upload a clearer copy.",
		)
		review_activity = frappe.db.get_value(
			"Comment",
			{
				"reference_doctype": "Client Verification Request",
				"reference_name": request.name,
				"content": ["like", "%Reviewer note:%"],
			},
			"content",
		)
		self.assertIn("Upload a clearer copy.", review_activity)
		self.assertIn(certificate.document_title, review_activity)

	def test_06_quotation_uses_customer_tax_id(self):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": f"Tax Field Test {frappe.generate_hash(length=8)}",
				"customer_type": "Company",
				"customer_group": self.get_valid_customer_group(),
				"territory": self.get_valid_territory(),
				"tax_id": "TEST-TAX-ID",
			}
		).insert(ignore_permissions=True)

		item_code = "Audit Consultation Service"
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": item_code,
					"item_group": "Services",
					"is_stock_item": 0,
				}
			).insert(ignore_permissions=True)

		quotation = frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Customer",
				"party_name": customer.name,
				"transaction_date": frappe.utils.nowdate(),
				"items": [{"item_code": item_code, "qty": 1, "rate": 100}],
			}
		).insert(ignore_permissions=True)

		self.assertEqual(quotation.custom_customer_tax_id, "TEST-TAX-ID")
		invoice = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": customer.name,
				"company": self.get_or_create_company(),
				"posting_date": frappe.utils.nowdate(),
				"due_date": frappe.utils.add_days(frappe.utils.nowdate(), 14),
				"items": [{"item_code": item_code, "qty": 1, "rate": 100}],
			}
		).insert(ignore_permissions=True)
		self.assertEqual(invoice.tax_id, "TEST-TAX-ID")
		self.assertEqual(
			frappe.get_meta("Sales Invoice").get_field("tax_id").fetch_from,
			"customer.tax_id",
		)


class TestCustomerLegalStructure(FrappeTestCase):
	def add_customer_child(self, customer_name, fieldname, values):
		customer = frappe.get_doc("Customer", customer_name)
		row = customer.append(fieldname, values)
		customer.save(ignore_permissions=True)
		return row
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		ensure_default_document_masters()

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _new_customer(self, legal_structure, **values):
		return frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": f"Legal Structure Test {frappe.generate_hash(length=8)}",
				"customer_type": legal_structure,
				"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
				or "Commercial",
				"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name") or "Kenya",
				**values,
			}
		)

	def test_customer_validation_and_defaults(self):
		customer = self._new_customer(
			"Company",
			custom_structure_subcategory="Private",
			custom_structure_subcategory_2="Company Limited by Shares",
			custom_structure_subcategory_3="Subsidiary",
		).insert(ignore_permissions=True)
		self.assertEqual(customer.custom_governing_law, "007/2021 of 05/02/2021")
		self.assertEqual(customer.custom_regulating_authority, "RDB")

		invalid = self._new_customer(
			"Company",
			custom_structure_subcategory="General partnership (GP)",
		)
		with self.assertRaises(frappe.ValidationError):
			invalid.insert(ignore_permissions=True)

		invalid_ngo = self._new_customer(
			"NGO",
			custom_structure_subcategory="International",
			custom_structure_subcategory_2="Specific Community Interest based",
		)
		with self.assertRaises(frappe.ValidationError):
			invalid_ngo.insert(ignore_permissions=True)

	def test_customization_setup_is_idempotent(self):
		setup_customizations()
		setup_customizations()
		self.assertEqual(
			frappe.get_meta("Customer").get_field("customer_type").options.splitlines(),
			list(CUSTOMER_TYPE_OPTIONS),
		)
		self.assertTrue(frappe.db.exists("Custom Field", {"dt": "Quotation", "fieldname": "custom_customer_tax_id"}))

	def test_jv_defaults_depend_on_subcategory_and_preserve_manual_values(self):
		self.assertEqual(
			structure_defaults("JV", "National")["law"],
			"Contract-based (no specific law)",
		)
		self.assertEqual(
			structure_defaults("JV", "International")["law"],
			"007/2021 of 05/02/2021",
		)
		self.assertEqual(
			validate_structure_subcategories(
				"JV", custom_structure_subcategory="Other"
			),
			("custom_structure_subcategory", "Other"),
		)

		customer = self._new_customer(
			"Partnership",
			custom_structure_subcategory="General partnership (GP)",
			custom_governing_law="A manually entered law",
			custom_regulating_authority="RRA",
		).insert(ignore_permissions=True)
		self.assertEqual(customer.custom_governing_law, "A manually entered law")
		self.assertEqual(customer.custom_regulating_authority, "RRA")

	def test_document_checklist_is_admin_added_and_idempotent(self):
		customer = self._new_customer("Partnership").insert(ignore_permissions=True)
		result = add_default_compliance_requirements(customer.name)
		self.assertGreater(result["created"], 0)
		self.assertTrue(
			any(
				row.document_title == "Partnership deed"
				for row in frappe.get_doc("Customer", customer.name).custom_compliance_certificates
			)
		)
		self.assertEqual(add_default_compliance_requirements(customer.name)["created"], 0)
		rows = default_document_rows("NGO")
		self.assertTrue(any(row["document_title"] == "RGB registration certificate" for row in rows))

	def test_client_document_master_integration(self):
		ensure_default_document_masters()
		self.assertTrue(frappe.db.exists("Client Document Master", "Certificate of incorporation"))
		self.assertTrue(frappe.db.exists("Client Document Master", "Trading licence"))

		custom_doc_title = f"Special Audit Clearance {frappe.generate_hash(length=6)}"
		frappe.get_doc(
			{
				"doctype": "Client Document Master",
				"document_title": custom_doc_title,
				"doc_type": "Licence",
				"has_expiry": 1,
				"issuing_authority": "Ministry of Finance",
				"short_alias": "SAC",
			}
		).insert(ignore_permissions=True)

		customer = self._new_customer("Company").insert(ignore_permissions=True)
		row = self.add_customer_child(
			customer.name,
			"custom_compliance_certificates",
			{
				"document_title": custom_doc_title,
				"is_required": 1,
			},
		)
		self.assertEqual(row.document_title, custom_doc_title)
		customer_doc = frappe.get_doc("Customer", customer.name)
		saved_row = next(r for r in customer_doc.custom_compliance_certificates if r.name == row.name)
		self.assertEqual(saved_row.document_title, custom_doc_title)
