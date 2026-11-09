
# TrustVault â€“ AI Usage Log

## Entry 1 â€“ November 2, 2026

**Task:** Creating the initial project folder structure.

**Prompt:** Asked AI to guide me in creating the required folders for a Python Flask project: `models`, `routes`, and `security`.

**AI output:** AI explained how to create the folders in VS Code Explorer.

**What was wrong:** The initial instructions did not make it clear enough that the main TrustVault folder must be selected each time. As a result, `routes` was accidentally created inside another folder.

**What I did instead:** I checked the Explorer structure, identified the incorrect nesting, and moved `routes` to the main TrustVault level. I also disabled Compact Folders to make the structure easier to inspect.

**Verification:** Checked the folder locations in VS Code Explorer.

**Related GitHub commit:** https://github.com/rangapujithadomala-ai/TrustVault/commit/1ad52bb




### 2026-11-02 â€” Authentication and email verification

**Work completed:** Implemented user registration, password validation and hashing, email verification using single-use tokens, login, and logout.

**Prompt / AI assistance:** Asked AI for help designing and implementing Flask authentication, email verification, and automated tests.

**AI output:** Suggested Flask routes, password hashing, verification-token handling, and pytest test cases.

**What needed correction:** Some test code needed adjustment to work with Flask's test client and session handling.

**What I did:** Reviewed and corrected the code, configured Gmail SMTP, tested registration and email verification, and added automated tests for invalid, expired and reused tokens, login failures, successful login, and logout.

**Verification:** Ran `pytest -v`; all 10 tests passed.

**Commit link:** https://github.com/rangapujithadomala-ai/TrustVault/commit/34ccd46



## Entry 3 â€“ November 3, 2026**

**Task:** Developing the frontend pages for the Viewer role.

**Prompt:** Asked AI to guide me in creating the Viewer dashboard, Shared with Me, Activity, Profile and Settings pages for TrustVault.

**AI output:** AI provided HTML structures, CSS styling and JavaScript guidance for the Viewer pages, including navigation, document tables, profile information, account settings and dark-mode support.

**What needed correction:** Some styling required adjustments for dark mode and consistent layouts. The Profile and Settings sections also needed clarification to keep role permissions and account controls separate.

**What I did:** Reviewed the generated code, made the suggested corrections, added shared styling and connected the theme selection across Viewer pages using JavaScript and localStorage.

**Verification:** Reviewed the five Viewer pages and checked the navigation, page structure and theme functionality. The pages currently use sample data and require backend integration.

**Commit Link:** https://github.com/rangapujithadomala-ai/TrustVault/commit/becdd1d




## Entry 4 â€“ November 4, 2026

**Task:** Developing the frontend pages for the Owner role.

**Prompt:** Asked AI to guide me in creating the Owner dashboard, My Documents, Upload Document, Shared Documents, Activity, Profile and Settings pages for TrustVault.

**AI output:** AI provided HTML structures, CSS styling and JavaScript guidance for the Owner pages, including document management, individual document-sharing permissions, sharing history, activity tracking, profile validation, account settings and appearance modes.

**What needed correction:** The dark mode did not update text colors correctly, and the Shared Documents and Activity tables occupied excessive space. The Settings page initially contained only the Appearance section instead of all six agreed sections.

**What I did:** Reviewed the generated code, corrected dark-mode text visibility, added compact table styling and expanded the Settings page to include Appearance, Notifications, Security, Privacy, Document Preferences and Account Preferences.

**Verification:** Reviewed the Owner frontend pages and their navigation and appearance settings. Further visual testing and backend integration are still pending. Notification, security and privacy controls are currently frontend preferences.

**Commit Link:** https://github.com/rangapujithadomala-ai/TrustVault/commit/37f9e95





## Entry 5 â€” November 6, 2026 â€” Server-side document authorization and file routes

**Prompt / fair summary:** I asked the AI to inspect my uploaded TrustVault source archive and connect document upload, named per-document read/edit grants, protected downloads, revocation, version uploads, archive/restore, and audit evidence while preserving my existing UI and keeping the security decision on the server.

**AI output:** It generated an integrated documents blueprint, private-storage handling, a permission helper, audit event calls, notification events, and authorization tests.

**What was wrong / what I checked:** The starting project only had an authorization helper and templates; there were no document upload/download/share endpoints. I also checked that the AI design did not accidentally make Admin a content bypass, that `read` is not treated as `edit`, and that file paths are UUID keys outside the public frontend. The hash chain is not immutable against a DB superuser and is explicitly documented as a limitation.

**What I did instead:** Added a dedicated document blueprint and tests for non-grantee read/download denial, read grant vs edit, revocation, and audit logging. Reviewed `security/authorization.py`, `routes/documents.py`, and `tests/test_document_authorization.py`.

**Verification status:** Static inspection and Python syntax compilation are pending final checks in this working package; the runtime pytest suite requires the project's dependencies and PostgreSQL/SQLite test setup. Do not claim this entry as passing tests until those are run.

**Commit link:** Pending a real commit; add the actual GitHub commit URL after committing these changes. No commit was fabricated.



## Entry 6 â€” November 6, 2026 â€” Audit chain and offboarding review

**Prompt / fair summary:** I asked AI to check the official threat model standard and wire a tamper-evident audit chain, denied-attempt logging, audit verification, account offboarding, and immediate access revocation into the existing code.

**AI output:** It generated an append-audit helper, Admin integrity-check endpoint, active-user session reload behavior, received-grant revocation, and owner-document transfer before offboarding.

**What was wrong / what I checked:** The naive hash implementation could produce a verification mismatch on SQLite because its timestamp is returned without timezone information. I normalized audit timestamps to UTC when hashing and checking. I also rejected Owner offboarding until all owned documents (including archived items) are transferred, because otherwise those files would be left with an inactive owner. A shared email-verification token table also needed a role guard so an Owner invitation token could not be consumed by the Viewer verification route. I added a password-hash digest snapshot in the session so password changes/deactivation invalidate previous sessions.

**What I did instead:** Added timestamp normalization, hash-chain verification, a transfer endpoint, a safeguard requiring transfer before deactivating an Owner, and role-specific token validation. Added tests for offboarding and Owner token confusion. The known residual risk is documented: a DB administrator can rewrite the whole chain unless its head is independently anchored.

**Verification status:** Code review performed; full runtime verification still needs to be run with installed dependencies. Replace this status after actual test execution.

**Commit link:** Pending a real commit; add the actual GitHub commit URL after committing these changes. No commit was fabricated.





## Entry 7 â€” November 6, 2026 â€” Authentication token and session hardening

**Prompt / fair summary:** I asked the AI to connect the remaining account flows (verification resend, password reset, profile/password updates, Admin invitation resend and offboarding) while preserving one-use token semantics, role boundaries, CSRF, audit logging, and the current pages.

**AI output:** It added token-backed endpoints and UI fetch calls, session invalidation based on a password-hash snapshot, Admin resend controls, and more authentication/offboarding tests.

**What was wrong / what I checked:** The first session-snapshot approach placed the full password hash in the signed browser session. I changed it to store only a SHA-256 digest of that password hash. I also found that the shared verification-token table could otherwise let an Owner invitation token be consumed by the Viewer verification endpoint; I added a role guard and a test for that token-confusion case. I checked that deactivation rotates the password hash and revokes received grants, so existing sessions and document access are invalidated.

**What I did instead:** Updated the user loader to compare the session digest to the current stored hash, invalidated prior password-reset/verification tokens on resend, implemented generic responses for reset/resend requests, and added tests for CSRF, offboarding, owner transfer, and token reuse/confusion.

**Verification status:** Python compile, Jinja template compilation, and JavaScript syntax checks are performed for the packaged source. Runtime pytest remains unverified here because the environment cannot resolve package downloads; run `pytest -v` after installing requirements locally and record the actual result.

**Commit link:** Pending a real commit and push; add the actual GitHub commit URL after committing these changes. No commit was fabricated.



## Entry 8 â€” November 8, 2026 â€” Owner invitation email and invitation-flow verification

**Prompt / fair summary:** I asked the AI to help complete and verify the Admin-to-Owner invitation flow, troubleshoot SMTP email delivery, and prepare the project for external testing without disturbing existing functionality.

**AI output:** It helped review the Admin invitation route, email service, Flask mail configuration, and environment variables. It also guided SMTP connectivity checks and verification of the invitation email flow.

**What was wrong / what I checked:** The invitation initially failed with a hostname-resolution error (`getaddrinfo failed`). I checked the configured SMTP server and port, confirmed that `smtp.gmail.com` resolved through DNS, and verified that TCP port 587 was reachable. The invitation email subsequently sent successfully. The exact cause of the earlier intermittent error was not conclusively established.

**What I did instead:** Kept the existing email service and configuration, checked the SMTP settings, and retried the Owner invitation. I confirmed that the invitation email was being sent successfully.

**Verification status:** Owner invitation email sending was manually verified. Full end-to-end testing by another user, including opening the official deployed invitation link and completing the invitation flow, is still pending.

**Commit link:** https://github.com/rangapujithadomala-ai/TrustVault/commit/f4b203764ce43d6ba1c4f0dcd2e1f2eb7012e993

## Entry 9 - November 9, 2026 - Phishing investigation, session logout response format, hosting legal transparency, and resilient database initialization

**Task / Prompt:** Investigated Google Safe Browsing's "Warning - phishing (web forgery) suspected" warning on the Railway deployment (https://trustvault-production-e0fd.up.railway.app/), resolved test failure on /auth/logout, corrected placeholder contact information and hosting provider legal mismatches, and hardened production initialization.

**AI output:** Suggested redirecting /auth/logout directly with an HTTP 302 redirect to /login.html?logout=1. Also suggested that Google Safe Browsing would clear immediately if text was rewritten.

**What was wrong specifically:**
1. Returning an HTTP 302 redirect from /auth/logout broke test_user_can_logout (which asserts status 200 OK with JSON response) and broke frontend/settings.js fetch handling, leading to test failure.
2. The AI previously left APP_BASE_URL defaulting to https://trustvault-p85t.onrender.com in config.py. On Railway, any email verification, password reset, or invitation link generated without an explicit environment override would contain a cross-domain URL pointing to Render, creating a severe phishing signal.
3. landing.html hardcoded contact@example.com, and privacy.html claimed the app was hosted on Render while deployed on Railway. Automated Safe Browsing crawlers heavily penalize new .up.railway.app subdomains presenting login forms with template placeholder emails and conflicting hosting assertions.
4. If DATABASE_URL was unconfigured or tables unmigrated on Railway, the app failed with 500/503 on database health queries and login attempts.

**What I did instead:**
1. Fixed routes/auth.py to return JSON 200 with { "message": "Logged out successfully.", "redirect": "/login.html?logout=1" }, restoring full compatibility with both the frontend fetch client and test_user_can_logout.
2. Updated config.py default APP_BASE_URL to https://trustvault-production-e0fd.up.railway.app and added an instance SQLite fallback for development/fallback resilience while preserving PostgreSQL for production.
3. Added automatic database table initialization and demo account seeding in app.py for evaluation readiness.
4. Added a clean /robots.txt endpoint (Allow: /) for crawler transparency.
5. Corrected privacy.html and terms.html to reflect Railway and Supabase infrastructure, attributed the application explicitly to the Snovasys RISE 2026 challenge by Ranga Pujitha, and replaced placeholder emails with the genuine contact address rangapujithadomala@gmail.com.
6. Added clear educational prototype disclaimers on both landing.html and login.html to eliminate deceptive branding appearance.
7. Added automated tests for /robots.txt and /health in tests/test_app.py.

**Verification:** Ran pytest -v; all 26 tests passed.

**Commit link:** https://github.com/rangapujithadomala-ai/TrustVault/commit/8966f3a
