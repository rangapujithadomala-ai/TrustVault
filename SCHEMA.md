# TrustVault database schema overview

SQLAlchemy model definitions in `models/` are the authoritative schema. `python create_tables.py` invokes `db.create_all()` to create missing tables; it does not modify columns of existing tables and is not a migration engine.

| Table / model | Main fields | Purpose / relationship |
|---|---|---|
| `users` (`User`) | id, name, unique case-insensitive email index, password_hash, role, is_active, email_verified, created_at | Admin / Owner / Viewer accounts; roles constrained to the three values |
| `documents` (`Document`) | id, owner_id FK, title, description, category, original_filename, storage_key, mime_type, size_bytes, current_version, created_at, updated_at, deleted_at | Document metadata and soft-archive state; owner FK points to `users` |
| `permissions` (`Permission`) | id, document_id FK, user_id FK, permission_type, granted_by FK, granted_at, revoked_at | Named per-document `read`/`edit` grants; active document/user unique partial index |
| `document_versions` (`DocumentVersion`) | id, document_id FK, version_number, storage_key, uploaded_by FK, checksum, created_at | File revision/checksum history; unique document/version pair |
| `audit_logs` (`AuditLog`) | id, actor_id FK nullable, document_id FK nullable, target_user_id FK nullable, action, outcome, ip_address, created_at, details JSON, previous_hash, event_hash unique | Append event record and SHA-256 chain; Admin verifies chain |
| `notifications` (`Notification`) | id, recipient_user_id FK, notification_type, message, related_document_id FK nullable, created_at, read_at | Recipient-specific inbox events; notification operations do not delete audit rows |
| `email_verification_tokens` (`EmailVerificationToken`) | id, user_id FK, token_hash unique, expires_at, used_at, created_at | Single-use email-verification and Owner-invitation tokens, hashed at rest |
| `password_reset_tokens` (`PasswordResetToken`) | id, user_id FK, token_hash unique, expires_at, used_at, created_at | Single-use one-hour password-reset token, hashed at rest |
| `starred_documents` (`StarredDocument`) | id, user_id FK, document_id FK, created_at, unique user/document | Personal star state; not an authorization grant |

**Important:** Document file contents are stored as files in the private storage directory. Only random storage keys are stored in database rows. The frontend directory must not contain document bytes.
