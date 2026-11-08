# Five-minute TrustVault demo recording plan

Record the deployed build in a private/incognito window with the seeded evaluation accounts. Only demonstrate steps that you have personally verified on the deployed URL. Keep this script as a plan, not proof of feature completion.

1. **0:00–0:35 — Problem and roles.** Briefly state the core problem: per-document grants and evidence of who reached a document. Show Admin, Owner and Viewer roles in README/API docs.
2. **0:35–1:15 — Admin.** Sign in as Admin, show user list/invitation, document metadata dashboard, audit log, and use “Verify Audit Chain”. Mention Admin does not bypass file-read permissions.
3. **1:15–2:05 — Owner upload.** Sign in as Owner, upload a harmless PDF through Upload Document, show it listed in My Documents, explain that file bytes live in private storage.
4. **2:05–2:55 — Share/revoke.** Grant a named verified Viewer `read`; show Shared Documents permission. Switch to Viewer and download only via the protected endpoint. Revoke from Owner and show the same Viewer download attempt fails immediately.
5. **2:55–3:50 — Attack attempt.** As Viewer, try the copied document ID through the protected detail/download route while grant is absent. Show denial and the corresponding denied event in Admin audit logs.
6. **3:50–4:30 — Audit integrity.** Show upload, permission grant/revoke, successful download and denied attempt entries; run audit-chain verification. Explain hash-chain limits honestly: a DB superuser can rewrite an unanchored chain.
7. **4:30–5:00 — Tests, threat model, gaps.** Show tests and `THREATS.md`; say what is not implemented or verified (e.g. external immutable anchoring, antivirus, multi-worker Redis rate limiting). Finish with live URL and role credentials.

**Before recording:** ensure deployment is live, private window sign-in works, sample accounts have credentials in evaluator README/form, test a grant and revoke, test denied access, verify chain, and avoid showing secrets or real confidential documents.
