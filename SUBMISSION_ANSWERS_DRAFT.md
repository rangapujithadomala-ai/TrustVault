# Snovasys My Submission — six-answer working draft

This draft must be updated to match the exact live deployment and the candidate's own words. Do not submit claims that have not been checked in the deployed system.

## 1. The problem I solved

TrustVault addresses confidential document sharing where a broad folder permission can expose unrelated files and where teams lack evidence of who accessed a document. I used document-specific grants for named accounts and server-side authorization on document operations. Access activity and refused attempts are recorded in an audit log.

## 2. What actually works right now

In the source package, Flask authentication includes Viewer email verification, invited Owner password setup, and email password-reset tokens. Owner upload, document metadata, named read/edit sharing, permission revocation, protected download, version upload, archive/restore, search, notifications, and audit-chain verification have routes. Admin account activation/deactivation and Owner document transfer are routed. Automated tests are included for cross-user read/download denial, read vs edit, revocation, audit events and auth flows.

**Before submission:** replace this paragraph with a feature-by-feature list of what was personally verified on the actual live URL. The runtime test suite and deployment are not confirmed by this bundle alone.

## 3. How to run it on your machine

Python 3.10+ and PostgreSQL are required. Create a PostgreSQL database, copy `.env.example` to `.env` and set the local secrets/connection/SMTP values, create/activate a virtual environment, install `requirements.txt`, then run:

```bash
python create_tables.py
python create_admin.py
python seed_demo.py   # after DEMO_OWNER_* and DEMO_VIEWER_* are set
python app.py
pytest -v
```

For production deployment install `requirements-deploy.txt` and use `gunicorn wsgi:app`, configure HTTPS, secure cookies, PostgreSQL and a persistent private storage volume.

## 4. Which AI tools I used

I used ChatGPT as a coding assistant to review the existing TrustVault source, suggest Flask route/model/security changes, help connect frontend actions to backend endpoints, and draft tests and documentation. I reviewed and adjusted its output rather than treating it as automatically correct. I documented assistance and corrections in `PROMPTS.md`.

## 5. What AI got wrong and what I fixed myself

During integration, I checked that audit-chain timestamp serialization remains consistent when SQLite returns naive datetimes; normalized timestamps to UTC. I also found that offboarding an Owner with active documents without first transferring ownership could leave those documents inaccessible, so the Admin route requires transfer first. I inspected the generated authorization logic to ensure Admin does not become an implicit content reader and that `read` grants do not allow metadata editing. I added tests for non-grantee direct access, download denial, read-only edit denial, and immediate revocation.

**Before submission:** add real commit URLs to the relevant `PROMPTS.md` entries and only describe issues you personally reviewed/verified.

## 6. What is not finished

The SHA-256 audit chain is tamper-evident but is not externally anchored/WORM immutable. File uploads are not antivirus-scanned or content-disarmed. Login throttling is process-local, not shared Redis-based. MFA and external guest sharing are not built. Online document editing is not built; `edit` means uploading a new version. Runtime pytest and deployed attack checks must be performed before claiming final verification. The demo credentials are listed in README. The live URL and verification that all seeded accounts open in a private window must be filled in after deployment.
