### Audit Portal

Client workspace for audit and compliance services.

### Installation

Install the app on a Frappe/ERPNext v16 bench using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd ~/frappe-bench
bench get-app <repo-url> --branch version-16
bench --site <site-name> install-app audit_portal
bench --site <site-name> migrate
bench build --app audit_portal
bench restart
```

Replace the repository URL and site name with the deployment's values. Before schema synchronization, `audit_portal.customizations.setup` idempotently installs the app-owned Customer and Quotation profile fields and Customer Type Property Setter. After child DocTypes are synced, the `after_migrate` hook provisions the Customer dossier tab and child table fields, and ensures the required portal roles exist. No customization depends on data from the development bench.

The app schema is provisioned directly from DocType definitions and `audit_portal/customizations.py`. No legacy data migrations or patch replay are needed when deploying in a new bench environment; install the app and migrate normally.

### Workspaces

- `/signup` lets a new organization request client portal access. The request is reviewed by staff before a Customer or User account is created.
- `/client-portal` gives an approved client a guided workspace for proposals, invoices, organization profile, Customer-linked contacts and addresses, ownership and board records, tax registrations, compliance documents/licences, and appointments.
- Staff use `/desk` to approve standalone `Client Signup Request` records and manage dossier records directly in Customer tabs: Ownership and Governance, Tax and Compliance, Banking, and Budgets. Customer forms can add a suggested legal-structure checklist. Each client upload creates a standalone `Client Verification Request` with its own status, private attachment, and activity timeline, like a signup request. Every upload is retained as a separate request; a newer upload supersedes an older pending request. The Customer child row links to the latest request, and the Customer timeline records upload and review summaries.

To authorize a staff member to review uploads, open their **User** record in Desk and add the **Audit Document Reviewer** role. No code change is needed for each staff member. This role has read/write access to verification requests, while review actions still enforce the request's current state and update the Customer compliance row and activity timeline. System Managers retain access.

To review a submission, use Desk search to open the **Client Verification Request** list. Filter by customer or review status, then open a request to see the private file and activity timeline. Set **Review Status** to `Verified` or `Rejected`, fill in the **Reviewer Note** if rejecting, and save. The submission fields are read-only at perm level 0; only the Review section (perm level 1) is editable by the reviewer. Saving triggers the controller, which stamps the reviewer, mirrors the outcome to the Customer compliance row, and appends an activity comment.

The client records workspace uses shared, field-driven frappe-ui components for lists, edit dialogs, and statuses. Customer-facing record APIs resolve the Customer from the authenticated session; the browser cannot choose an organization to read or mutate. Evidence is stored as a private Frappe File and must be reviewed by authorized staff.

The app intentionally does not copy all 35 custom DocTypes from the Corporate Services reference. ERPNext `Customer` is the canonical organization record; its standard `customer_type` field is extended through an app-owned Property Setter to include legal-structure choices, while audit registration details are app-owned Custom Fields on Customer. Structure sub-categories are dependent selects, and the server validates them and supplies governing-law and authority defaults without replacing manually entered values. Customer-owned dossier requirements and profile data are stored in Customer fields and child tables. Signup staging remains standalone because it exists before a Customer is provisioned; each uploaded document also creates a standalone `Client Verification Request` to preserve its review lifecycle and activity timeline. Existing Client Profile values, standalone dossier rows, and current review states/files are migrated safely. The app uses standard Frappe/ERPNext records for customers, contacts, addresses, appointments, quotations, invoices, and files, plus focused app child DocTypes for ownership, tax registration, banking, budgets, and compliance requirements, backed by `Client Document Master` for pickable compliance document definitions. Insurance, assets, loans, providers, memberships, intellectual property, change-request application, reminders, and operational reports are not yet implemented.

The signup and client portal pages use Vue 3 and Frappe UI with a minimal Frappe page renderer; there is no Jinja-rendered application interface. Staff workflows use native Desk forms and lists.

The frontend requires Node.js 20.19 or newer. From the app directory:

```bash
cd frontend
npm ci
npm run dev
```

The dev server defaults to the bench port plus 80 (usually `8080`). If that port is in use, set `FRAPPE_UI_DEV_PORT` to another port, for example `FRAPPE_UI_DEV_PORT=8081 npm run dev`.

The Vite development page does not have Frappe's server-rendered CSRF token. To test signup, staff actions, or quotation decisions, use a disposable development site and disable CSRF there with `bench --site <dev-site> set-config ignore_csrf 1`. Never disable CSRF on a production site.

For production assets, run `npm run build` from `frontend/` (or `bench build --app audit_portal` from the bench root). The build writes static assets under `audit_portal/public/frontend/`; the page renderer serves those assets directly.

After deploying a code update, run `bench --site <site-name> migrate`, rebuild the app assets when frontend code changed, then restart the bench processes. To verify the app against a development site:

```bash
cd ~/frappe-bench
bench --site <site-name> run-tests --app audit_portal
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/audit_portal
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
