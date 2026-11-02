
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

**Commit link:** To be added after committing this milestone.