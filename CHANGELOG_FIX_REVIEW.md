# TrustVault – latest correction pass

## Changes in this pass
- Added the missing `ProxyFix` import used when `TRUST_PROXY=true`; without it, that deployment setting would raise a `NameError`.
- Replaced the Viewer Settings password redirect with an in-page password form that calls the existing `/auth/change-password` endpoint using the endpoint's exact JSON field names and CSRF header. It displays the server's success/error response and does not sign the user out.
- Removed the duplicate password-change control and prompt flow from the Viewer Profile page. Password changes are now presented only in Viewer Settings.
- Added an Owner Settings password form using the same existing authenticated endpoint and clear in-page feedback.
- Updated the Admin resend-verification success response to `Verification email sent successfully.`; the route still returns an error response if mail delivery raises an exception.

## Validation and limitations
- Python source compilation passed (`python -m compileall -q .`).
- JavaScript syntax checks passed (`node --check` for the frontend JavaScript files).
- The pytest suite could not be run in this environment because Flask is not installed (`ModuleNotFoundError: No module named 'flask'`). No passing test-suite claim is made.
- The upload route and upload form were inspected and their endpoint/CSRF wiring is present. The actual upload workflow still requires an end-to-end run against the project's configured PostgreSQL database and private storage directory.
- The deployed verification link cannot be confirmed from this ZIP alone. The registration route builds the link from the incoming request host (`request.url_root`); on a reverse-proxy deployment, set `TRUST_PROXY=true` only when the app is behind the expected trusted proxy and configure the deployment's public host correctly.
- Notification dropdown markup and click handling are present in the current dashboard. Styling and end-to-end notification delivery still require browser testing with generated notifications.
- No database, `.env`, Git history, or deployment settings were modified.
