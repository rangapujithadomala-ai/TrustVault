# TrustVault — secure document sharing with a real audit trail

TrustVault is a Flask/PostgreSQL document-sharing prototype for the Snovasys RISE challenge. Its core design is **deny by default**: the server checks a live document-specific grant for every metadata read/download/edit request. No document bytes are placed in the public frontend folder or exposed through a public bearer URL.

## Live Deployment & Evaluator Access

- **Live Application URL:** https://trustvault-production-e0fd.up.railway.app/
- **Status / Health Endpoint:** https://trustvault-production-e0fd.up.railway.app/health
- **Author & Contact:** Ranga Pujitha (rangapujithadomala@gmail.com)

## Roles

- **Admin:** invite Owner accounts, manage account activation/offboarding, inspect document metadata and audit/security events, verify the audit hash chain. Admin is not a document content superuser.
- **Owner:** upload, organize, search, update metadata, upload new versions, archive/restore owned documents, grant/revoke `read` or `edit` to a named active/verified Owner or Viewer, inspect permissions/activity.
- **Viewer:** see and download documents only when a live document grant allows read or edit. Viewer cannot upload/share/archive the Owner's source document.

## Features in this codebase

- Password hashing, Viewer email verification, invited Owner password setup, and single-use email password-reset tokens.
- Flask-Login sessions, CSRF protection, active-account reload, process-local login throttle.
- Private Supabase Storage bucket for uploaded documents; filename/extension/size validation. The optional demo sample is stored under a private local path.
- Document-specific live grants, grant/revoke, notification events, secure download route, revision uploads, archive/restore.
- Audit records for successful and denied access paths, with SHA-256 hash chain and Admin chain-verification endpoint.
- Search endpoint filters by title/category/owner/date; Owner/Viewer data scopes are enforced.
- Starred-document API (a star is not an access grant).
- Automated tests for cross-user authorization, download restrictions, revocation, audit evidence, and authentication.

## Run locally from a clean clone

1. Install Python 3.10+ and PostgreSQL. Create a database named `trustvault`.
2. Copy `.env.example` to `.env`. Fill `SECRET_KEY`, `DATABASE_URL`, and SMTP fields. Never commit `.env` or disclose mail/database passwords.
3. Windows PowerShell:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python create_tables.py
   python create_admin.py
   python app.py
   ```
   macOS/Linux:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python create_tables.py
   python create_admin.py
   python app.py
   ```
4. Open `http://127.0.0.1:5000/login.html`. The public `/health` endpoint checks DB connectivity for deployment monitoring.
5. Run automated tests: `pytest -v`.
To create challenge demo accounts, use `seed_demo.py` only against an isolated **non-production** database. Set `TRUSTVAULT_DEMO_MODE=true` and provide unique account values through the `ADMIN_*`, `DEMO_OWNER_*`, and `DEMO_VIEWER_*` environment variables. There are no built-in demo credentials; the script refuses production environments and refuses to modify an account that already exists. Never enable this mode or reuse demo credentials with production data. An Admin can invite additional Owners; a Viewer registers and verifies their own email link.

## Deployment

- Deploy with a production WSGI server, e.g. `gunicorn wsgi:app` after installing `requirements-deploy.txt`. Do not use Flask's debug server in production.
- Configure `APP_ENV=production` (Railway/Render are detected automatically), Supabase PostgreSQL as `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_BUCKET`, `SECRET_KEY`, and SMTP. Production startup rejects missing, malformed, local-only, or non-PostgreSQL database URLs; it does not fall back to SQLite. `SESSION_COOKIE_SECURE` is forced on in production; keep HTTPS enabled. If the optional demo sample uses `TRUSTVAULT_STORAGE`, keep that path on a persistent **private** volume and never expose it through a static web server. Verify the Supabase bucket is private; the application uses the server-side Supabase key to access it.
- Removing automatic demo seeding does not remove demo accounts already present in an existing database. Before deploying this code, use the Supabase dashboard or another approved administrative process to review any previously seeded demo accounts and disable or rotate them. This project does not modify production users or data automatically.
- Run `python create_tables.py` for initial schema creation. This project uses `db.create_all`; it is not a migration engine. For schema evolution use Flask-Migrate/Alembic and review migrations before production.
- Confirm the deployment URL in a private/incognito window, test email verification/invitation delivery, run the security tests against the deployed environment, and check the `/admin/audit-integrity` endpoint as Admin.
- Keep Git repository private before the challenge deadline per the challenge rules. Verify no `.env`, secrets, database dumps, or uploaded files exist in git history before making it public.
- Google Transparency Report currently marks the listed Railway URL unsafe for pages that may trick visitors into sharing personal information or downloading software. This audit did not establish the cause. Review Google Search Console's Security Issues report, inspect/clean the deployed site, and request a Google review when appropriate; application changes do not themselves clear a Safe Browsing warning.

## Security notes and known limitations

See [`THREATS.md`](THREATS.md) for mitigations and accepted risks, and [`API.md`](API.md) for endpoint roles. The audit hash chain is tamper-evident, not an immutable external ledger. Latest-row locking serializes common concurrent appends, but the hash head is not externally anchored and a DB superuser can rewrite it. The login limiter is process-local; use shared Redis-backed throttling in multi-worker deployment. Upload validation does not include antivirus/content-disarm scanning. MFA, external guest sharing, and online document editing are deliberately not implemented. Edit access means upload a revised version. Previously downloaded copies cannot be remotely revoked.

## Challenge hand-in checklist

- [ ] Public GitHub repo at the appropriate time, meaningful real commits through the week
- [ ] Live URL opens in private window; persistent DB and private storage
- [ ] If demo accounts are needed, provision unique credentials only on an isolated non-production database; do not publish or reuse production credentials
- [ ] `THREATS.md`, `PROMPTS.md`, `API.md`, schema/setup scripts, automated tests
- [ ] Five-minute demo video, concise write-up, honest unfinished items
- [ ] My Submission form filled, links verified, and “I am done” submitted before deadline

## AI usage

AI assistance is documented in `PROMPTS.md`. It includes errors/rejected approaches and pending commit-link fields; replace those fields with actual commit links after making the corresponding genuine commits. Do not fabricate prompt history or backdate commits.


## Evaluator Access

The project includes an Admin dashboard for reviewing user management,
document management and administrative functionality.

**Demo Admin Credentials**

- Login URL: http://127.0.0.1:5000/login.html
- Email: admintrustvault@gmail.com
- Password: TrustVault@2026

**Important:** These credentials are for evaluation purposes only.
The application must first be configured and started locally using
the setup instructions provided above.

The live deployment is currently experiencing a runtime issue.