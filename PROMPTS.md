
# TrustVault – AI Usage Log

## Entry 1 – November 2, 2026

**Task:** Creating the initial project folder structure.

**Prompt:** Asked AI to guide me in creating the required folders for a Python Flask project: `models`, `routes`, and `security`.

**AI output:** AI explained how to create the folders in VS Code Explorer.

**What was wrong:** The initial instructions did not make it clear enough that the main TrustVault folder must be selected each time. As a result, `routes` was accidentally created inside another folder.

**What I did instead:** I checked the Explorer structure, identified the incorrect nesting, and moved `routes` to the main TrustVault level. I also disabled Compact Folders to make the structure easier to inspect.

**Verification:** Checked the folder locations in VS Code Explorer.

**Related GitHub commit:** https://github.com/rangapujithadomala-ai/TrustVault/commit/1ad52bb




### 2026-11-02 — Authentication and email verification

**Work completed:** Implemented user registration, password validation and hashing, email verification using single-use tokens, login, and logout.

**Prompt / AI assistance:** Asked AI for help designing and implementing Flask authentication, email verification, and automated tests.

**AI output:** Suggested Flask routes, password hashing, verification-token handling, and pytest test cases.

**What needed correction:** Some test code needed adjustment to work with Flask's test client and session handling.

**What I did:** Reviewed and corrected the code, configured Gmail SMTP, tested registration and email verification, and added automated tests for invalid, expired and reused tokens, login failures, successful login, and logout.

**Verification:** Ran `pytest -v`; all 10 tests passed.

**Commit link:** https://github.com/rangapujithadomala-ai/TrustVault/commit/34ccd46



## Entry 3 – November 3, 2026**

**Task:** Developing the frontend pages for the Viewer role.

**Prompt:** Asked AI to guide me in creating the Viewer dashboard, Shared with Me, Activity, Profile and Settings pages for TrustVault.

**AI output:** AI provided HTML structures, CSS styling and JavaScript guidance for the Viewer pages, including navigation, document tables, profile information, account settings and dark-mode support.

**What needed correction:** Some styling required adjustments for dark mode and consistent layouts. The Profile and Settings sections also needed clarification to keep role permissions and account controls separate.

**What I did:** Reviewed the generated code, made the suggested corrections, added shared styling and connected the theme selection across Viewer pages using JavaScript and localStorage.

**Verification:** Reviewed the five Viewer pages and checked the navigation, page structure and theme functionality. The pages currently use sample data and require backend integration.

**Commit Link:** https://github.com/rangapujithadomala-ai/TrustVault/commit/becdd1d




## Entry 4 – November 4, 2026

**Task:** Developing the frontend pages for the Owner role.

**Prompt:** Asked AI to guide me in creating the Owner dashboard, My Documents, Upload Document, Shared Documents, Activity, Profile and Settings pages for TrustVault.

**AI output:** AI provided HTML structures, CSS styling and JavaScript guidance for the Owner pages, including document management, individual document-sharing permissions, sharing history, activity tracking, profile validation, account settings and appearance modes.

**What needed correction:** The dark mode did not update text colors correctly, and the Shared Documents and Activity tables occupied excessive space. The Settings page initially contained only the Appearance section instead of all six agreed sections.

**What I did:** Reviewed the generated code, corrected dark-mode text visibility, added compact table styling and expanded the Settings page to include Appearance, Notifications, Security, Privacy, Document Preferences and Account Preferences.

**Verification:** Reviewed the Owner frontend pages and their navigation and appearance settings. Further visual testing and backend integration are still pending. Notification, security and privacy controls are currently frontend preferences.

**Commit Link:** Pending
