# TrustVault API Authorization Reference

All POST/PATCH/DELETE mutations require a valid Flask-WTF CSRF token (`X-CSRFToken`). JSON errors are returned where appropriate. Authentication uses Flask-Login session cookies. Admin is not implicitly granted document-content access.

| Method / path | Who may call | Effect / enforcement |
|---|---|---|
| `GET /health` | Public | Checks database connectivity for deployment health checks |
| `POST /auth/register` | Public | Creates Viewer account; email verification required |
| `POST /auth/login` | Public | Valid credentials, active account, verified email; process-local throttling |
| `GET /auth/verify-email/<token>` | Public with token | Single-use token; redirects to verification status page |
| `POST /auth/resend-verification` | Public | Generic response, rate-limited; sends fresh 24-hour token for eligible unverified Viewers |
| `GET,POST /auth/accept-owner-invitation/<token>` | Invited Owner with token | Owner chooses password; invitation single-use/expiry |
| `POST /auth/forgot-password` | Public | Generic response; sends a one-hour single-use reset token only to active verified accounts |
| `POST /auth/reset-password` | Public with reset token | Validates token/password, updates password, invalidates prior password-snapshot sessions |
| `POST /auth/profile/update`, `/auth/change-password` | Authenticated user | Updates current user's name or password; password requires current credential |
| `POST /auth/logout` | Authenticated | Ends login session; sidebar sends a CSRF-protected POST |
| `GET /admin/dashboard`, `/admin/users`, `/admin/documents`, `/admin/audit-logs`, `/admin/security-alerts`, `/admin/notifications`, `/admin/settings`, `/admin/profile` | Admin | Admin views system metadata/events and notification metadata for all recipients; no content-read bypass |
| `POST /admin/invite-owner` | Admin | Invites a named email as Owner |
| `POST /admin/users/<id>/resend-invitation` | Admin | Invalidates previous pending Owner invitation tokens and sends a fresh 24-hour invitation |
| `POST /admin/users/<id>/resend-verification` | Admin | Resends verification to an unverified Viewer and invalidates previous verification tokens |
| `POST /admin/users/<id>/deactivate` | Admin | Deactivates user and revokes received grants; Owner must first transfer active owned docs |
| `POST /admin/users/<id>/activate` | Admin | Reactivates a verified account |
| `POST /admin/users/<id>/transfer-documents` | Admin | Transfers documents from an Owner to another active verified Owner |
| `GET /admin/audit-integrity` | Admin | Verifies hash chain and reports first failed event |
| `GET /owner/dashboard`, `/owner/my-documents`, `/owner/upload-document`, `/owner/shared-documents`, `/owner/received-documents`, `/owner/archived`, `/owner/starred`, `/owner/activity`, `/owner/profile`, `/owner/settings` | Owner | Owner pages scoped to owned docs and live received grants |
| `POST /documents/upload` | Owner | Multipart upload; extension/size validation; private storage; upload/version/audit rows |
| `GET /documents/?q=&owner=&category=&start=&end=` | Owner or Viewer | Search by title, owner name, category, and date; Owner sees own docs, Viewer sees live grants only |
| `GET /documents/<id>` | Owner or current read/edit grantee | Document metadata; logs access |
| `GET /documents/<id>/download` | Owner or current read/edit grantee | Protected file download; logs success/denial |
| `PATCH /documents/<id>/metadata` | Owner only | Updates title/category |
| `POST /documents/<id>/share` | Owner only | Grants named active verified Owner/Viewer `read` or `edit`; notification + audit |
| `GET /documents/<id>/permissions` | Owner only | Lists active grants |
| `POST /documents/<id>/revoke/<permission_id>` | Owner only | Revokes a grant immediately; notification + audit |
| `POST /documents/<id>/version` | Owner or current `edit` grantee | Uploads revised file as new version; not online editing |
| `POST /documents/<id>/archive`, `/restore` | Owner only | Soft archive/restore |
| `POST /documents/<id>/star` and `GET /documents/starred` | Owner/Viewer with current read grant | Personal star; never changes access |
| `GET /notifications/` | Authenticated user | Only recipient's notification list |
| `POST /notifications/<id>/read`, `/read-all`, `/clear-read`, `/clear-all` | Authenticated user | Mutates only current user's notifications |
| `DELETE /notifications/<id>` | Authenticated user | Deletes only current user's notification |
| `GET /viewer/dashboard`, `/viewer/my-documents`, `/viewer/shared-with-me`, `/viewer/starred`, `/viewer/activity`, `/viewer/profile`, `/viewer/settings` | Viewer | Viewer pages scoped to live grants |

## Clean clone / database setup

1. Python 3.10+ recommended. Create a PostgreSQL database and configure `.env` based on `.env.example` (if supplied by deployment operator). Never commit real secrets.
2. `python -m venv venv` then activate it (`venv\\Scripts\\activate` on Windows; `source venv/bin/activate` on Linux/macOS).
3. `pip install -r requirements.txt`
4. `python create_tables.py`
5. `python create_admin.py` (interactive initial admin creation).
6. `python app.py` (local development only; use a production WSGI server and HTTPS for deployment).
7. `pytest -v`.

Document storage uses `instance/private_documents` by default. Configure `TRUSTVAULT_STORAGE` to a persistent private directory on deployment. Do not mount it as public static files.
