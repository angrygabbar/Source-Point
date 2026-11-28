# Integrations guide

All external integrations are **optional** and **off until configured**. Nothing is simulated: when
a provider is not configured the related action is unavailable (or a delivery is recorded as
skipped/failed) and the UI says so. Credentials are entered in **Settings → Integrations**, stored
in `integration_configs` with secrets encrypted by `ENCRYPTION_KEY` (Fernet) and never returned to
the browser (only "configured" indicators). Each provider also has a feature flag that must be on.

| Type | Provider key | Config fields | Secret fields | Feature flag |
|---|---|---|---|---|
| email | `smtp` | host, port, username, from_address, use_tls | password | `email` |
| sms | `msg91` | sender_id, flow_id | auth_key | `sms` |
| sms | `twilio` | account_sid, from_number | auth_token | `sms` |
| whatsapp | `meta_whatsapp` | phone_number_id, default_template, template_language | access_token | `whatsapp` |
| push | `webpush` | vapid_public_key, vapid_subject | vapid_private_key | `push` |
| payment | `razorpay` | key_id | key_secret, webhook_secret | `online_payments` |
| ai | `openai_compatible` | base_url, model, monthly_token_limit, input_cost_per_1k, output_cost_per_1k | api_key | `ai` |
| video | `zoom` | account_id, client_id, host_user | client_secret | `video_meetings` |
| video | `google_meet` | client_id, calendar_id | client_secret, refresh_token | `video_meetings` |

Environment fallbacks: `BREVO_*` or `SMTP_*` (email) and `VAPID_*` (push) are used when an institute has no
enabled configuration of that type. The SourcePoint deployment syncs its Brevo key into the Institute
stack's private environment file; the key is not stored in Git or the Institute database.

## Email (Brevo or SMTP)
The SourcePoint deployment uses Brevo's transactional email API for Institute notifications and
password resets. A standalone deployment can instead configure an SMTP relay (SES, SendGrid SMTP,
Microsoft 365, Gmail Workspace relay) with `SMTP_*` settings or in Settings → Integrations. Notification
templates are seeded per institute for each supported event and can be edited in the application. Email
is enabled automatically when a provider is configured unless an institute has explicitly disabled it.
Without email, password resets are issued by administrators as reset links (Users → Reset link).

## SMS
- **MSG91** – India DLT: create a Flow whose template uses a single variable named `message`,
  register the sender id and template with DLT, then enter the `flow_id`.
- **Twilio** – Account SID, auth token and an SMS-capable `from_number`.

## WhatsApp Business Cloud API (Meta)
Requires a verified WhatsApp Business Account, a phone number id, a permanent access token and
**approved message templates** (business-initiated messages must use templates). Set
`default_template` to an approved template with one body parameter; the notification text is
passed as that parameter.

## Web Push
Generate VAPID keys (e.g. `npx web-push generate-vapid-keys`), enter them, enable `push`. Users
opt in from Profile → Notifications (browser permission prompt). iOS requires the PWA to be
installed to the home screen (iOS 16.4+).

## Razorpay (online fee payment)
1. Enter `key_id`, `key_secret` and a `webhook_secret`.
2. In the Razorpay dashboard create a webhook to
   `https://<your-domain>/api/v1/webhooks/razorpay/<institute_id>` for `payment.captured`
   (and optionally `payment.failed`) using the same secret. The institute id is shown in
   Settings → General.
3. Enable `online_payments`. Students/parents see **Pay online** on open invoices.

Flow: `POST /payments/online/order` creates a gateway order → Razorpay Checkout →
`POST /payments/online/verify` checks the HMAC signature and records the payment idempotently;
the webhook records it if the browser never returns. Duplicate gateway payment ids are rejected by a
unique index. Refunds are recorded in the ERP; gateway-side refunds must be issued in the Razorpay
dashboard (not automated).

## AI (OpenAI-compatible)
Any endpoint implementing `POST {base_url}/chat/completions` (OpenAI, Azure OpenAI via compatible
gateway, self-hosted vLLM/Ollama with OpenAI API). Used for: question generation from text,
summaries, lesson-plan drafts, homework/feedback drafts, report insights. All AI output is stored as
an `ai_request` draft that a staff member must review/approve; generated questions enter the
question bank as `draft` and require approval. Student personal data is not sent unless
`ai.allow_student_data` is enabled. Monthly request/token limits are enforced. AI never changes
marks, attendance or finance records.

## Video meetings
- **Zoom** – Server-to-Server OAuth app with `meeting:write:admin` scope; `host_user` is the Zoom
  user (email or id) who hosts the meetings.
- **Google Meet** – OAuth client + refresh token for a Google account with Calendar access; meetings
  are created as Calendar events with conference data on `calendar_id` (default `primary`).

Without a video provider, staff can still paste a meeting link manually on a session or LMS lesson.

## Outbound webhooks
Settings → Webhooks: register endpoints (HTTPS recommended) and event types. Deliveries are signed
with `X-ClassFlow-Signature: <hex HMAC-SHA256 of the raw body>` once a secret is set (row action
*Set signing secret*, `PUT /api/v1/webhook-endpoints/{id}/secret`; stored encrypted), retried with back-off, and blocked
for private/loopback addresses (SSRF protection).
