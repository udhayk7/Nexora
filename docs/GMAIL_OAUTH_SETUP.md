# Gmail OAuth 2.0 Integration & Security Guide

Nexora integrates with Google Gmail via OAuth 2.0 strictly for recruiter communications, draft creations, and user-initiated email delivery.

---

## 1. Setup Instructions in Google Cloud Console

1. **Create/Select a Google Cloud Project**:
   - Navigate to [Google Cloud Console](https://console.cloud.google.com).
   - Create a project named `Nexora-Production` (or select your existing project).

2. **Enable Required APIs**:
   - In **APIs & Services > Library**, enable the **Gmail API**.

3. **Configure OAuth Consent Screen**:
   - Set User Type to **External** (or Internal for Google Workspace organizations).
   - Fill in App Name ("Nexora"), User Support Email, and Developer Contact Information.
   - Add Scopes:
     - `https://www.googleapis.com/auth/gmail.compose` (Create drafts and send messages).
     - `https://www.googleapis.com/auth/gmail.send` (Send messages on user's behalf).
     - `https://www.googleapis.com/auth/userinfo.email` (Identify connected Gmail address).

4. **Create OAuth 2.0 Credentials**:
   - Go to **APIs & Services > Credentials > Create Credentials > OAuth client ID**.
   - Application type: **Web application**.
   - Authorized JavaScript origins:
     - `http://localhost:3000` (development)
     - `https://app.nexora.com` (production)
   - Authorized redirect URIs:
     - `http://localhost:8000/api/v1/integrations/google/callback` (development)
     - `https://api.nexora.com/api/v1/integrations/google/callback` (production)
   - Copy the generated `Client ID` and `Client Secret`.

5. **Configure Nexora Environment**:
   ```bash
   GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_client_secret
   GOOGLE_REDIRECT_URI=https://api.nexora.com/api/v1/integrations/google/callback
   GMAIL_TOKEN_ENCRYPTION_KEY=your_secure_32_byte_aes_key
   ```

---

## 2. Token Security & Storage Architecture

### 2.1 AES-256-GCM Token Encryption
- OAuth tokens (`access_token` and `refresh_token`) are **never stored in plaintext**.
- Encryption uses authenticated AES-256-GCM via `app.core.encryption`.
- A 12-byte random initialization vector (IV) is generated per encryption operation, and an authentication tag verifies ciphertext integrity.
- If the encryption key is missing or corrupted, Nexora refuses token decryption and marks the connection as needing re-authorization.

### 2.2 Tamper-Proof State Tokens
- During OAuth initiation (`/api/v1/integrations/google/auth-url`), Nexora generates a signed state parameter using HMAC-SHA256 (`user_id.action.timestamp.hmac`).
- The redirect callback validates the signature before proceeding, preventing CSRF and authorization hijacking.

---

## 3. Strict Consequential Action Safeguards

Nexora enforces strict behavioral constraints on all Gmail interactions:
1. **Explicit User Approval Required**: Nexora will never automatically dispatch an email without explicit confirmation. `confirm_send=True` is required on execution endpoints.
2. **Draft-First Workflow**: By default, recruiter outreach creates a Gmail draft (`gmail_draft_id`), allowing the user to review the message in Gmail prior to sending.
3. **Recipient Validation**: Recipient email addresses are validated against strict RFC-5322 regex formatting before any draft or message payload is generated.
4. **Instant Revocation**: Users can disconnect their account at any time via `POST /api/v1/integrations/google/disconnect`. This immediately revokes the OAuth token with Google servers and deletes encrypted credentials from the database.

