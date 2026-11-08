# TrustVault Threat Model (RISE Challenge)

**Scope:** The current Flask/PostgreSQL app, private file storage, authenticated users, deployment configuration, and document-sharing APIs. This is a working threat model, not a claim that the service is invulnerable.

## Permission model and decision points

- Admin manages accounts/invitations, observes metadata and audit/security events, and can deactivate users. Admin is **not** a universal document reader.
- Owner owns uploaded documents, can change metadata, upload versions, grant `read` or `edit` to a named active/verified Owner or Viewer, revoke grants, archive/restore, and transfer ownership only through Admin-assisted offboarding.
- Viewer can read/download only documents with a live per-document `read` or `edit` grant. `edit` includes read. Viewer cannot upload, share, change metadata, archive, restore, or delete an Owner's original.
- Access decisions happen server-side: per-document read/edit routes call `can_access_document` through the shared authorization helper; upload/share/archive/restore routes enforce Owner role or ownership, and list/search routes are scoped to the caller's owned documents or live grants. Deny by default. A revoked grant is queried live on every document request; no signed public file URL is issued.

## Threats considered, mitigations, and accepted gaps

| Threat / attack | Mitigation in code | Residual risk / accepted limitation |
|---|---|---|
| Viewer guesses another document UUID and calls detail endpoint | Live grant lookup; denied attempt is audit logged; endpoint returns 403/404 | Need deployment attack exercise and route-by-route test coverage continuously |
| Viewer directly calls download URL without grant | Download endpoint checks permission before file bytes; file not in public static directory | Private local disk may be ephemeral on some hosts; configure persistent private volume/object storage |
| User keeps access after owner revokes grant | Revocation sets `revoked_at`; authorization checks DB every request; no public bearer links | Already downloaded copies cannot be remotely erased; explicitly accepted and should be stated to the share recipient |
| Disabled account reuses an old Flask session | Flask-Login user loader returns only active user; admin revokes grants | password-hash digest snapshot in the session invalidates sessions after password change/reset; deactivation rotates the stored hash. Flask session signing key rotation/session store revocation could be needed for a larger deployment |
| Viewer tries to edit/read-restricted metadata or archive | Owner check or `edit` grant is enforced server-side | This challenge app's editor operation is upload-a-new-version, not collaborative in-browser editing |
| Owner shares to arbitrary/unregistered email or self | Share endpoint accepts only active, verified Owner/Viewer account, validates permission, denies self | External guest sharing is deliberately not built |
| Duplicate or conflicting permission grant | Unique active document/user index; existing active grant is updated | Concurrent grant race should be handled with retry/constraint response in production |
| Unsafe extension, huge file, or obvious fake PDF/image | extension allow-list, 15 MiB app limit, secure filename, UUID storage key, selected PDF/image magic checks, no public static path | DOC/DOCX/PPT/XLS/CSV validation is extension based and not full malware scanning / content disarm; accepted for prototype, do not upload malware |
| Path traversal via filename or storage key | `secure_filename`; random storage key; only server derives storage path; attachment response | Private storage disk permissions must be set correctly by host operator |
| Audit entry altered/deleted | SHA-256 hash chain links each row; Admin endpoint verifies chain; denied attempts are recorded | Hash chain is tamper-evident, not tamper-proof. DB superuser can rewrite whole chain or delete final row absent external anchor. A download success proves the server authorized and began serving the file, not that the client completed saving it. Accepted prototype gap; production should periodically anchor hashes to independent write-once log |
| Audit record claims wrong identity/time | actor identity from authenticated session, UTC timestamp, request IP stored, server event on access/denial | IP can be proxied/spoofed unless trusted proxy config is correct; clocks depend on host |
| Login brute force | process-local throttle: eight failures per IP+email in 15 minutes | In-memory limiter resets on restart and is per worker. Password-reset request throttling uses the same process-local store. Production must use shared Redis/database rate limiter and MFA; accepted gap |
| CSRF against session-authenticated mutations | Flask-WTF CSRF protection, frontend sends `X-CSRFToken`, SameSite=Lax cookie; sidebar logout is POST | Validate all deployed pages/forms and HTTPS cookie setting; reverse-proxy setup can affect |
| Session cookie theft / browser exposure | HttpOnly, SameSite=Lax; configurable Secure cookie; permanent session timeout default 30 minutes; password-hash digest snapshot invalidation; password hashing via Werkzeug scrypt | HTTPS must be enforced at deployment; no MFA; browser malware remains out of scope |
| User enumeration in registration/login | Login failure response is generic for invalid credentials; registration reveals duplicate email | Registration duplicate-account response may disclose existence; accepted usability tradeoff, could genericize |
| Owner leaves with documents that have grantees | Admin transfer endpoint transfers documents to another verified active Owner before deactivation; deactivation revokes the departing account's received grants | Admin must execute transfer before offboarding; active Owner document ownership is not automatically reassigned |
| Notification deletion used to erase evidence | Notifications are separate; delete/clear endpoints only delete recipient notifications; audit table untouched | Notifications are not evidentiary; audit log is the evidence stream |
| Stored XSS through filenames, names, metadata | secure filenames, templates use escaping; JSON client use textContent in notifications | Review all template interpolation and browser JS sinks before deployment; strict CSP not configured yet |
| Database/API availability, resource exhaustion | upload caps and query limit 200; login throttling | No general request throttling, antivirus, backup automation, or DB connection pool sizing for scale |
| Public repo leaks secrets | `.gitignore` excludes `.env`; never commit secrets | Must inspect actual git history and hosting environment before making repo public; user must rotate any committed secret |

## Tests expected

The automated suite includes authenticated tests for: a document owner upload, a non-granted viewer denied direct read and download, a read grant allowing download but not edit, an edit grant permitting version upload, access revoked immediately, denied-request audit evidence, upload validation, single-use password reset/resend verification, CSRF rejection, Viewer offboarding grant/session revocation, Owner document transfer before deactivation, and hash-chain detection after event-detail tampering. These should be run after installing `requirements.txt`; no test result is claimed in this document.

## Deliberately not built

- Online document editing, external guest links, folder-inherited permissions, AI-generated access grants, antivirus/content disarm, MFA, and durable cross-worker rate limiting.
- AI may assist an owner, but no AI feature can independently widen document access. There is no autonomous AI sharing in the current build.
- Production-grade immutable audit anchoring (independent WORM/log provider) is not implemented. We explain this honestly rather than claim the DB hash chain is immutable.
