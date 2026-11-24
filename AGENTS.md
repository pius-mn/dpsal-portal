# Audit Portal — Development Guide

## Purpose and direction

`audit_portal` is a Frappe/ERPNext client workspace. Treat this repository as the source of truth. The goal is to keep extending the application as a Vue 3 frontend built with **frappe-ui**, backed by Frappe DocTypes and Python APIs.

The client experience has multiple interactions—not just a landing page. Preserve and extend the access-request and approval flow, customer-scoped compliance work, quotation decisions, invoice review/download, and the supporting feedback, loading, filtering, and error states. For new workflows, implement the complete user journey and its server-side behavior rather than adding a visual-only control.

## Non-negotiable architecture

- Build customer-facing pages with Vue 3 and `frappe-ui` from `frontend/`. Use Frappe UI components for interactive controls and feedback, with Vue state/composition for page behavior.
- Do not add Jinja templates, website HTML page shells, a second frontend framework, or a parallel component library. Frappe's Python renderer may return the minimal HTML mount shell and inject request-specific bootstrap values; it must not render the application UI.
- Keep Frappe as the source of truth for identity, authorization, business rules, and persistence. A hidden button or client-side filter is never an access-control boundary.
- Keep ERPNext/Frappe document operations and validations on the server. Avoid duplicating business rules in Vue.
- Do not create a separate ERPNext `Company` for each client. Use the existing ERPNext Company where accounting documents require one; represent portal clients as `Customer` records.
- Keep changes inside this app directory. Do not edit the bench configuration, site data, Frappe/ERPNext core, or another app.
- Preserve accessible labels, keyboard focus, responsive layouts, and reduced-motion behavior when extending the UI.

## Current implementation

### Frontend

- `frontend/src/main.js` mounts `PortalApp.vue` at `/client-portal` and `SignupApp.vue` at `/signup`. Staff use Frappe Desk rather than a separate staff portal.
- `frontend/src/lib/frappe.js` calls whitelisted Frappe methods, sends same-origin credentials and CSRF tokens, and also supports private multipart file uploads.
- `frontend/src/pages/PortalApp.vue` presents the dashboard, submitted quotations and responses, invoices, and the customer records workspace.
- `frontend/src/pages/ClientRecordsWorkspace.vue` provides organization profile editing, dependent legal-structure subcategories, Customer-linked Contact and Address management, shareholder/beneficial-owner/board-member records, tax registrations, uploads for staff-assigned documents, and Appointment booking/cancellation.
- `frontend/src/components/RecordCollection.vue`, `RecordEditorDialog.vue`, and `StatusPill.vue` provide shared list, field-driven create/update dialog, and status presentation patterns for the records workspace. Keep record definitions and field allowlists aligned between the frontend and `audit_portal/api/client_records.py`.
- `frontend/src/pages/SignupApp.vue` submits public access requests and displays validation, submission, and signed-in states.
- `audit_portal/public/js/client_verification_request.js` adds Desk form actions for authorized staff to verify a pending upload or request a new upload with a required reviewer note. `audit_portal/public/js/customer.js` adds Customer Documents shortcuts for suggested requirements and the customer-filtered verification-request list.
- `frontend/src/style.css` imports `frappe-ui/style.css` and defines the app's Tailwind setup, shared visual tokens, and accessible focus/reduced-motion behavior.
- `frontend/vite.config.js` provides Vite development routes/proxy and emits production assets under `audit_portal/public/frontend/`.
- `audit_portal/page_renderer.py` serves the minimal portal mount shell, bootstraps the current user and CSRF token, and disables caching.

### Backend and data

- `audit_portal/api/signup.py` exposes the guest signup endpoint. It validates and rate-limits submissions and creates only a Pending `Client Signup Request`; it must never provision a live account from the public request.
- `audit_portal/provisioning.py` restricts approval to `System Manager` or `Administrator`, then idempotently provisions/links a `Customer`, Website `User`, `Audit Client` role, and Customer `User Permission`.
- `audit_portal/api/portal.py` resolves exactly one Customer from the current user's User Permission or linked Contact. Ambiguous customer mappings are denied. It returns customer-scoped submitted quotation and invoice data, and verifies ownership before quotation responses and invoice details/PDF downloads.
- `audit_portal/api/client_records.py` exposes an explicit read/write allowlist for a customer's organization profile, ownership/governance records, tax registrations, assigned compliance documents, private evidence files, and Appointments. Clients cannot create or edit document requirements; upload and download operations resolve the Customer server-side, and submitted files enter `Pending Review`.
- `audit_portal/legal_structure.py` is the canonical legal-structure taxonomy and server-side validation/default source. `audit_portal/customizations.py` installs Customer/Quotation profile fields and the Customer Type Property Setter before sync, then installs Customer child-table fields only after the referenced DocTypes have synced as child tables. Keep site-specific data out of this setup.
- `Client Verification Request` uses **Frappe perm levels** to enforce who can review a document. Submission fields (customer, document title, attachment, submitted by/on) sit at perm level 0 and are `read_only` for everyone. The Review section (status, reviewed by/on, reviewer note) sits at perm level 1. `Audit Document Reviewer` holds a perm-level-1 `write` permission, so reviewers edit the status and reviewer note directly in Desk and save normally. The `ClientVerificationRequest.before_save()` controller validates the transition (only `Pending Review → Verified/Rejected`, rejection requires a note, attachment must exist), stamps `reviewed_by` and `reviewed_on` automatically, mirrors the outcome to the linked `Compliance Certificate` child row on the Customer, and appends an activity comment. There is no separate `staff.py` whitelist API.
- `Audit Document Reviewer` is created during app installation/migration and has perm-level-0 `read`/`write` and perm-level-1 `read`/`write` on `Client Verification Request`. Perm level 0 `write` is required for Frappe's `has_permission` check and to open the record in write mode in Desk; the submission fields remain individually `read_only` as a UI constraint. Perm level 1 `write` grants access to the Review section (status, reviewer note). To authorize an individual, an administrator assigns this role on the user's Desk **User** record; no per-user code/configuration is needed. System Managers retain both perm levels. The controller enforces state transitions rather than relying on a hard-coded role list.
- Review flow: use Desk search for the `Client Verification Request` list; filter by Customer or status, open a record to see the private attachment and activity timeline, then set **Review Status** to `Verified` or `Rejected`, fill in the **Reviewer Note** if rejecting, and save. Each upload is a separate record; the Customer compliance row links to the latest request.
- App-owned schemas are under `audit_portal/audit_portal/doctype/`: `Client Document Master` is the master catalog for client compliance documents; `Client Shareholder`, `Client Beneficial Owner`, `Client Board Member`, `Client Tax Registration`, `Client Bank Account`, `Client Budget Line`, and `Compliance Certificate` are child tables on Customer. `Client Signup Request` remains standalone as pre-provisioning staging, and `Client Verification Request` is standalone to represent each document submission and review lifecycle. `Customer` is the canonical organization record; audit-specific profile fields and dossier tabs are app-owned Custom Fields on Customer. `Address`, `Appointment`, `Contact`, `Quotation`, `Sales Invoice`, and `File` remain Frappe/ERPNext records.
- `audit_portal/hooks.py` registers `/signup` and `/client-portal`, the custom renderer, Customer/Quotation/Client Verification Request Desk scripts, installation/migration setup for the `Audit Document Reviewer` role, legal-structure validation, and signup validation/provisioning document events.
- The app's schema is provisioned directly through DocType JSON definitions and the idempotent `before_migrate` / `after_migrate` customization setup in `customizations.py`. The app requires no legacy data migrations when deploying in a fresh bench environment.
- `audit_portal/tests/test_audit_portal.py` covers pending-only signup, approval and idempotent provisioning, cross-customer reads/writes, ambiguous customer mapping denial, denied guest/unmapped access, staff authorization/document review, legal-structure validation/defaults, and idempotent suggested document requirements.

The portal's data APIs intentionally use server-resolved customer identity. Do not add a `customer` parameter as an authorization input or broaden a query beyond the resolved Customer.
The implemented customer records are a focused first set, not a port of the reference app's 35 DocTypes. Banking details, insurance, assets, loans, providers, memberships, intellectual property, change-request application, reminders, and staff reports remain future work. Contact and Address records use standard Frappe DocTypes and are exposed only through Customer Dynamic Links; shared records are read-only to prevent changes from affecting another linked organization. Never expose password/credential records or copy a standard ERPNext record into a duplicate custom DocType.

## User journeys to preserve and extend

1. **Request access:** A Guest submits organization/contact details at `/signup`. The server validates the data, enforces duplicate/rate checks, and records a Pending request. No Customer or User is created at this stage.
2. **Approve access:** An authorized administrator approves the staging record in Desk. The approval flow provisions or reuses the relevant records and associates them with the request. Keep this operation safe to retry.
3. **Enter the portal:** `/client-portal` requires an authenticated user. Each portal API independently resolves that user's Customer and denies missing or invalid mappings.
4. **Maintain organization information:** A client reads and updates its profile, Customer-linked contacts and addresses, shareholder, beneficial-owner, board-member, and tax-registration records. The legal-structure taxonomy drives subcategory options; Frappe validates saved values and fills governing-law/authority only when blank. Every mutation checks record ownership and applies a server-side field allowlist.
5. **Request and submit evidence:** Staff may add the suggested legal-structure checklist from a Customer form, then reviews and adjusts the `Compliance Certificate` child rows in the Customer's Tax and Compliance tab. The client sees only assigned requirements and uploads a private PDF/image to them; clients cannot create or edit requirement metadata. Each upload creates a `Client Verification Request` record with its own history. Staff reviews these from their Desk list or from the Customer's Documents menu. Every read/download checks ownership through the resolved Customer.
6. **Book and manage meetings:** A client reads only Appointments linked to its Customer and may book or cancel its own future appointment.
7. **Review commercial work:** A client sees only its submitted quotations/invoices. Proposal responses and invoice details/download actions re-check ownership server-side.
8. **Extend workflows:** For new create/update flows, define who may act, the allowed fields and state transitions, server validation, ownership checks, success/error states, and tests before exposing controls.

Keep the distinction clear between existing features and proposed extensions in code and documentation. Do not claim a workflow is implemented until its frontend, server endpoint, permissions, and tests are present.

## Corporate-services domain expectations

The domain direction below is informed by the separate reference app at `/home/pius/Downloads/DPSingh_ERPNext16_AI_Agent_Knowledge_Base/dps_erpnext16_ai_agent_knowledge_base/corporate_services`. Its source-grounded guide is [Corporate Services AGENTS.md](/home/pius/Downloads/DPSingh_ERPNext16_AI_Agent_Knowledge_Base/dps_erpnext16_ai_agent_knowledge_base/corporate_services/AGENTS.md). Use it as a product and workflow reference, not as code to copy: that app is Jinja-based, has incomplete change-request application, and contains permission and sensitive-data concerns. The targets below are **future capabilities** unless identified in Current implementation.

### Product scope to grow toward

Grow the current audit dashboard into a secure customer workspace around one customer-linked organizational dossier. The dossier should be extensible across:

- **Organization and governance:** legal structure and registration, regulatory details, addresses, ownership/shareholders/beneficial owners, board/committee members, related parties, and employee disclosures.
- **Operations and finance:** bank accounts, loans, fees, budgets, assets, insurance, memberships, intellectual property, business activities, and service providers.
- **Compliance:** certificates and private evidence files, tax registrations/deadlines, licences/renewals, document status, expiry reminders, and audit history.

These are domain categories, not a mandate to add every field or reproduce the reference app's 35 DocTypes wholesale. Before modeling each category, identify the user task, sensitivity, lifecycle, retention, ownership, and source of truth. Prefer focused linked DocTypes/child tables over one oversized form, and avoid storing credentials or payment secrets in portal-readable records.

### Reuse existing Frappe/ERPNext DocTypes first

The reference app's DocType names describe its implementation, not a requirement to recreate them. Before adding a DocType, inspect the installed Frappe/ERPNext schema and lifecycle. Extend or link the standard DocType when its business meaning matches; add a custom DocType only for data or workflow ERPNext does not represent. In this repository, the relevant standard schemas are present under the bench's `apps/frappe` and `apps/erpnext` trees.

| Reference concept | Preferred model in this app |
|---|---|
| Client organization details | Keep ERPNext `Customer` as the single organization/accounting record. `Customer.customer_type` is the canonical Customer Type/Legal Structure selector, with legal-form options added through an app-owned Property Setter; do not add a duplicate legal-structure field. The TIN belongs in `Customer.tax_id`; other audit registration details belong in app-owned `Customer` Custom Fields. Migration copies existing profile data only when the target is empty or already matches, and stops on conflicts. |
| Contact, primary contact, and client addresses | Use Frappe `Contact` and `Address`, linked to `Customer` through their Dynamic Link tables. Do not duplicate names, emails, phone numbers, or postal addresses in a custom profile unless a distinct historical/legal snapshot is required. Mark the selected billing Address as primary so ERPNext can default it on new selling documents. |
| Client users and portal mapping | Use Frappe `User`, `Contact.user`, and `User Permission` with `allow = "Customer"` for identity and access mapping. `Client Signup Request` remains the app's public staging record; approval provisions/links standard records. Pick one canonical mapping strategy and enforce uniqueness rather than silently combining User Permission and Contact fallback mappings. |
| Quotations and invoices | Use ERPNext `Quotation` and `Sales Invoice` as the records of truth. Sales Invoices use the standard Customer tax ID field; the app adds a Quotation tax-ID Custom Field and fills it from the selected Customer. Primary Customer-linked Addresses are available as defaults on new quotations and invoices. Portal APIs may expose only submitted, customer-owned records and must not copy their amounts, status, or line items into custom tables. |
| Customer bank accounts | Evaluate ERPNext `Bank Account` first; its schema supports a party type and dynamic party link. Use it only when its semantics and permissions suit the customer-owned account. Treat account numbers and related data as highly sensitive; never expose them merely because the standard DocType exists. |
| Appointments | Use ERPNext `Appointment` for booking, availability, party, and cancellation lifecycle. Add only app-specific fields or server rules that the standard record cannot express. |
| Uploaded compliance evidence | Store binaries as Frappe `File` attachments using private files and explicit ownership checks on every download. Do not create a parallel file-storage DocType. |
| Follow-up work and communication | Prefer Frappe `ToDo`/`Communication` where their semantics fit. Do not introduce a custom task, notification, or message model just to render a portal list. |
| Compliance obligations, certificates, tax registrations, licences, renewals | Use the focused compliance-document and tax-registration records for evidence review and statutory filing details. Do not create a general-purpose `Client Compliance Item` checklist. |
| Change proposals and client dossier details | Use a custom `Client Change Request` only for the client-proposal/review/apply workflow that standard ERPNext records do not supply. Use a child table for proposed field changes when structured before/after values are needed. Keep organization attributes on `Customer` rather than adding a parallel profile master. |
| Client employees, owners, boards, related parties, providers, memberships, intellectual property, insurance | First determine whether an existing standard record actually represents the client's relationship (for example, `Employee` represents an employee of an ERPNext `Company`, not automatically a customer's staff member). Use native records where the meaning matches; otherwise add small customer-linked custom records only for the specific use case. Never force unrelated data into a standard DocType just to avoid customization. |
| Fees, budgets, and payments | Use ERPNext selling/accounting records (`Quotation`, `Sales Order`, `Sales Invoice`, `Payment Entry`, and related standard records) for actual commercial transactions. Add a custom compliance/service record only for non-accounting obligations that those transaction records do not model. |

This mapping is a decision guide, not proof that every listed workflow is implemented or appropriate for every site. Confirm DocType fields, supported links, permissions, and installed-version behavior before wiring a feature. Do not change ERPNext core schemas; add app-owned Custom Fields/fixtures or app DocTypes through this app when justified.

### Custom DocType gate

Before creating or expanding a custom DocType, document:

1. The domain behavior that cannot be represented by an existing Frappe/ERPNext DocType or an app-owned Custom Field/link.
2. Its canonical parent (`Customer` or a justified one-to-one profile), ownership rule, field sensitivity, retention, and staff/client permission matrix.
3. Its lifecycle and transitions, including who creates, reviews, applies, rejects, cancels, or archives it.
4. Whether it needs independent reporting, audit history, attachments, or child rows.
5. Tests proving customer isolation, unauthorized state transitions are denied, and private attachments cannot be fetched cross-customer.

Keep the custom model lean. Do not port the reference app's full 35-DocType schema as a batch, and do not mirror standard Customer, Contact, Address, User, Appointment, Quotation, Sales Invoice, Bank Account, or File data into app-owned duplicates.

### Customer workspace capabilities

Plan the Vue/frappe-ui customer experience as coherent modules, not a single growing dashboard. The customer route uses `frontend/src/pages/PortalApp.vue`; staff workflows use standard Desk forms and lists. The modules below describe both implemented and planned capabilities. Use `frappe-ui` as the sole component library for the customer portal; the existing Tailwind utilities may provide layout and spacing, but do not build a parallel set of custom form controls, dialogs, or feedback widgets:

- **Overview:** engagement and profile completion, compliance health, pending reviews, overdue/expiring items, upcoming tax/licence dates, and relevant next actions.
- **Documents and compliance:** customer manages their own document and licence records and uploads evidence privately. Uploads enter `Pending Review`; staff verifies or rejects with a reason; the system records who changed status and when and notifies the customer.
- **Taxes and licences:** customer-scoped read views with registration/filing or renewal dates, deadlines, status, and actionable reminders.
- **Organization profile:** a curated, mostly read-only view of the customer's legal, contact, ownership, and governance dossier. Never expose the entire profile or all child rows by default.
- **Change requests:** customer proposes changes only to explicitly allowed targets and fields. Support a review lifecycle such as `Submitted → Under Review → Clarification Required / Approved / Rejected → Applied`; apply approved changes on the server, atomically and idempotently, with before/after audit data. Do not treat approval as completion until the target record has actually been updated.
- **Appointments:** show available slots, book against the authenticated customer's account, and permit cancellation only for that customer's eligible future appointments.

Keep messages, empty states, filters, confirmation dialogs, and error recovery in the Vue UI. Use Frappe UI components and patterns; do not reintroduce the reference app's Jinja pages, vanilla-JS portal, or separate custom widget library.

### Staff operations and governance

The product has both customer and staff workflows. Staff currently use native Desk forms and lists for signup approval, Customer dossier management, and verification-request review. Staff-facing Vue/frappe-ui screens for onboarding/profile completion, change-request review/application, and operational reporting for compliance health, expiring certificates, insurance dues, overdue tax, and onboarding progress are planned, not implemented. Keep staff actions server-authorized and auditable.

Do not grant all staff `System Manager` just to make these screens work. Define least-privilege staff roles and permission matrices when the workflow is implemented; preserve the current `System Manager` restriction until such roles and tests exist. A client must never access another customer's dossier through a list, detail, attachment, report, export, or mutation endpoint.

### Identity and data-boundary decisions

The reference implementation resolves a portal user through `Customer.portal_users` to a linked Client Profile and uses standard Frappe `/login`; it does **not** implement an admin-approved sign-in token or custom session creation (`Corporate Services AGENTS.md`, section 7). The current `audit_portal` instead resolves Customer through User Permission or Contact. Do not silently combine these mappings: choose and document one canonical mapping for the app, enforce one intended customer/profile relationship, and test missing, ambiguous, and cross-customer mappings. If admin-approved invite links are a required product feature, design token generation, single use, expiry, revocation, delivery, and session establishment explicitly; do not imply that the reference app already provides them.

Treat bank, employee, ownership, tax, and especially portal credential data as sensitive. The reference profile contains such fields, but its existence is not permission to expose them. Return purpose-specific DTOs with field allowlists, keep uploaded files private, authorize each download by parent ownership, and add tests for direct API access as well as visible page flows.

## API and security requirements

- Add whitelisted methods in the appropriate module under `audit_portal/api/`; keep endpoints small and validate all input server-side.
- For every read, resolve the logged-in user to a Customer on the server and apply that Customer to every relevant query. Deny Guest and unmapped users.
- For every mutation, resolve ownership again, validate the target document's state and allowed transition, and use Frappe's permission/document APIs where applicable. Never trust a record name, customer identifier, role, or status supplied by the browser.
- Keep guest-accessible methods explicitly marked `allow_guest=True`; expose only the minimum operation needed before login.
- Send state-changing requests as POST with the Frappe CSRF token. Use the existing `callFrappe` helper unless a well-justified shared transport change is needed.
- Do not suppress failed requests or return success-shaped fallbacks. Show actionable errors and keep server-side validation authoritative.
- Avoid leaking private customer, invoice, or request details in errors, logs, URLs, or client bootstrap data.
- Keep provisioning idempotent and preserve normal Frappe transaction behavior. Do not send welcome emails during tests.

## Extending the frappe-ui application

- Build the entire new interaction in `frontend/`: loading/empty/error/success states, form validation feedback, disabled/submitting controls, and responsive presentation.
- Prefer existing frappe-ui components and existing shared helpers before creating a new component or abstraction. Keep a component local until reuse is real.
- Keep frontend state in Vue; do not introduce inline scripts, global mutable state, or direct DOM-driven business logic.
- Add the matching server API, validation, and authorization before wiring a mutating control.
- Add/modify DocTypes and migrations only when the data model requires it. Follow the existing Frappe DocType layout and role/permission conventions; update fixtures/hooks only when necessary.
- Provision app-owned Customer/Quotation Custom Fields and Property Setters through the idempotent `before_migrate` customization setup. Keep `patches.txt` for irreversible or one-time data transformations; guard legacy imports when source DocTypes are absent. Test a fresh install and an upgrade path when changing the setup/migration boundary.
- Update `README.md` when developer setup, routes, or build behavior changes. Keep this guide aligned with the actual implementation; mark planned work as planned, not current behavior.
- Use the repository's existing dependency manager and lockfile. If upgrading frappe-ui, select a current release compatible with the project, update `frontend/package-lock.json`, and verify the production build and app behavior; do not hand-edit installed packages.

## Routes, build, and verification

The app maps `/client-portal` and `/signup` to the `portal` renderer through `audit_portal/hooks.py`. Staff use `/desk`; do not recreate their workflows under a separate `/audit-team` web route. The customer frontend route selection lives in `frontend/src/main.js`; keep route registration and renderer behavior consistent when adding a client page.

Frontend development and production build (Node.js `>=20.19`):

```bash
cd ~/frappe-bench/apps/audit_portal/frontend
npm ci
npm run dev
npm run build
```

On a new bench, install the app on the target site and migrate normally. The `before_migrate` and `after_migrate` hooks create/update all schema customizations and roles idempotently:

```bash
cd ~/frappe-bench
bench get-app <repo-url> --branch version-16
bench --site <site-name> install-app audit_portal
bench --site <site-name> migrate
bench build --app audit_portal
bench restart
```

Run Frappe tests from the bench root against the configured development site:

```bash
cd ~/frappe-bench
bench --site erpnext.localhost run-tests --app audit_portal
```

After frontend changes, run the production build. After API, permission, DocType, or provisioning changes, run the app tests and add regression coverage for the changed behavior—especially cross-customer read and mutation isolation. Never disable CSRF on a production site.
