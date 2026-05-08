# GhostWriter AI (Haqdaar)

> WhatsApp-first agentic system that helps Indian families file post-death EPF and insurance claims — with multilingual voice support, document quality checks, auto-generated government forms, and Aadhaar eSign.

---

## What It Does

When a breadwinner dies, the family must file claims across EPF, EDLI insurance, state pension schemes, and more. The process requires multiple forms, document verification, and compliance checks — typically taking months with a lawyer. Haqdaar does this over WhatsApp in under 10 minutes.

The user sends a message or voice note. The system:
1. Detects their language from the first voice message (Telugu, Hindi, or English) — no setup needed
2. Guides them through onboarding in their language via text and voice notes (Sarvam TTS)
3. Collects all 14 fields needed to fill Form 5(IF): claimant details, bank account, PF number
4. Verifies uploaded documents using Gemini Vision (6-point quality check)
5. Discovers all eligible schemes and calculates total entitlement
6. Runs a 100-point compliance audit
7. Generates and delivers the official EPFO Form 5(IF) pre-filled with all their details
8. Sends an Aadhaar eSign link to make the form legally submittable

---

## Project Status

| Feature | Status |
| :--- | :--- |
| WhatsApp webhook (Meta Cloud API) | Live |
| Multilingual onboarding — Telugu, Hindi, English | Live |
| Voice notes via Sarvam TTS (OGG Opus) | Live |
| Voice input via Sarvam STT (saarika:v2.5) | Live |
| Auto language detection from voice (Unicode script) | Live |
| Natural language voice answers for choice questions | Live — Gemini fallback |
| WAMID deduplication (no duplicate replies) | Live |
| Document QualityAgent (Gemini Vision) | Live — 6-point pre-flight check |
| EntitlementAgent | Live — EPF, EDLI, PMJJBY, state schemes |
| ComplianceAgent (100-point audit) | Live |
| Form 5(IF) overlay (official EPFO template) | Live — 14-field pre-filled PDF |
| EPF Form 20 fallback | Live |
| Aadhaar eSign (demo mode) | Live — visual signature block, OTP page |
| Claim status tracking ("where is my claim?") | Live |
| GriefSupportAgent | Live — empathy intercept before claims flow |
| ReconciliationAgent | Live — identity mismatch + affidavit generation |
| DisputeAgent | Live — denial letter objection drafting |
| B2B Claims-as-a-Service API | Live — multi-tenant, API key auth, webhooks |
| Admin Dashboard | Live — `/dashboard` |
| Celery deadline alerts | Live — daily 9 AM IST reminders |
| PostgreSQL persistence | Live — full async state machine |

---

## Agentic Swarm

| Agent | Role |
| :--- | :--- |
| EntitlementAgent | Discovers eligible schemes (EPF, EDLI, PMJJBY, state pensions) from family data |
| ComplianceAgent | 100-point audit — triggers form generation when score hits 100 |
| QualityAgent | Gemini Vision 6-point check: legibility, lighting, framing, doc type, signature, stamp |
| GriefSupportAgent | Detects grief/distress, responds with empathy, optionally pauses claims flow |
| ReconciliationAgent | Detects name mismatches across documents, drafts affidavits |
| DisputeAgent | Analyzes claim denial letters, drafts legal-grade objection responses |
| FormAgent | Overlays family data onto official Form 5(IF) PDF template; falls back to ReportLab Form 20 |

---

## Voice Flow

When a user sends a voice message:
1. OGG Opus (WhatsApp format) is converted to WAV via pydub
2. Sarvam STT (`saarika:v2.5`) transcribes with `te-IN` hint by default
3. Language is detected from Unicode script ranges in the transcript (reliable vs API language_code):
   - Telugu: U+0C00–U+0C7F
   - Hindi (Devanagari): U+0900–U+097F
   - Tamil: U+0B80–U+0BFF
   - Kannada: U+0C80–U+0CFF
4. On the first voice message, `preferred_language` is auto-set and the language-selection step is skipped
5. For multiple-choice questions (employment type, relationship, state), natural speech is resolved via a Gemini prompt mapping free text to the canonical option
6. All replies are sent as both text and voice note in the detected language

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| Backend | FastAPI (async Python) |
| LLM | Google Gemini 2.5 Flash |
| STT / TTS / Translation | Sarvam AI — saarika:v2.5 / bulbul:v2 |
| Messaging | Meta WhatsApp Cloud API v18 |
| Database | PostgreSQL via async SQLAlchemy |
| Migrations | Alembic |
| Task queue | Celery + Redis |
| PDF generation | ReportLab + pypdf overlay |
| Audio | pydub + FFmpeg (OGG Opus to WAV) |
| Infrastructure | Docker Compose |

---

## Architecture

```
User (WhatsApp)
      |
      v
Meta Cloud API --> POST /webhook/whatsapp (ngrok / production URL)
                          |
                          v
                    FastAPI (main.py)
                    [WAMID dedup — no retries]
                          |
          ┌───────────────┼───────────────┐
          v               v               v
    GriefAgent      OnboardingFlow    B2B API (/api/v1/b2b)
                          |
          ┌───────────────┼───────────────┐
          v               v               v
   QualityAgent   EntitlementAgent  ComplianceAgent
                          |
                    FormAgent (Form 5IF overlay)
                          |
                    PDF + eSign link → WhatsApp
```

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Meta WhatsApp Business App (developer account)
- API keys: Google Gemini, Sarvam AI
- ngrok (for local webhook testing)

### Setup

1. Clone and configure:
    ```bash
    git clone https://github.com/vaibhavnagdeo18/ghostwriter.git
    cd ghostwriter
    cp .env.example .env   # fill in your keys
    ```

2. Start services:
    ```bash
    docker-compose up --build
    ```
    Alembic migrations run automatically on startup.

3. Expose webhook:
    ```bash
    ngrok http --domain=your-domain.ngrok-free.app 8000
    ```

4. Configure Meta:
    - Set webhook URL: `https://your-domain.ngrok-free.app/webhook/whatsapp`
    - Verify token: value of `WHATSAPP_VERIFY_TOKEN` in `.env`
    - Subscribe to `messages` field
    - Subscribe WABA to app: `POST /{waba_id}/subscribed_apps`

5. Send "hi" to your WhatsApp test number to start a claim.

### Environment Variables

```
GOOGLE_API_KEY=
SARVAM_API_KEY=
SARVAM_BASE_URL=
WHATSAPP_ACCESS_TOKEN=        # System User token (non-expiring)
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_BUSINESS_ACCOUNT_ID=
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/ghostwriter
REDIS_URL=redis://redis:6379/0
STORAGE_PATH=./documents
SECRET_KEY=
APP_BASE_URL=                 # your ngrok or production domain
```

---

## Onboarding Fields (14 steps)

| Step | Field | Description |
| :--- | :--- | :--- |
| 1 | preferred_language | Telugu / Hindi / English — auto-detected from voice |
| 2 | breadwinner_name | Name of the deceased |
| 3 | date_of_death | Date of death |
| 4 | employment_type | Government / Private / Business / Daily Wage |
| 5 | had_epf | Whether the deceased had an EPF account |
| 6 | claimant_name | Name of the person filing the claim |
| 7 | relationship | Relationship to deceased |
| 8 | claimant_dob | Claimant date of birth |
| 9 | claimant_address | Full address with PIN code |
| 10 | pf_account_no | EPF / UAN number (or skip) |
| 11 | bank_account | Bank account number for claim payment |
| 12 | bank_ifsc | IFSC code |
| 13 | death_certificate | Photo upload — Gemini Vision quality check |
| 14 | state | State for scheme eligibility lookup |

---

## B2B API

Partners can integrate Haqdaar as a Claims-as-a-Service layer.

```bash
# Create partner (returns raw API key once)
POST /api/v1/b2b/partners

# Initialize a claim case
POST /api/v1/b2b/initialize
Header: X-API-KEY: <key>

# Upload a document
POST /api/v1/b2b/upload-doc/{case_id}
Header: X-API-KEY: <key>

# Get case status
GET /api/v1/b2b/status/{case_id}
Header: X-API-KEY: <key>
```

Results (including generated PDFs as base64) are delivered to the partner's webhook URL.

---

## eSign Flow

After Form 5(IF) is generated, the system:
1. Creates a unique signing token and transaction ID
2. Sends a signing URL to the user over WhatsApp: `/esign/{token}`
3. The user opens the page and submits any 6-digit OTP (demo mode)
4. A visual Aadhaar eSign block is overlaid on the PDF (blue border, name, transaction ID, date, "Verified by Haqdaar AI | CDAC eSign")
5. The signed PDF is sent back to the user over WhatsApp

Production swap: replace the OTP handler in `services/esign_service.py` with a call to the CDAC / NSDL Aadhaar eSign gateway.

---

## Project Structure

```
ghostwriter/
├── main.py                        # Webhook handlers, onboarding state machine
├── agents/
│   ├── entitlement_agent.py
│   ├── compliance_agent.py
│   ├── quality_agent.py
│   ├── support_agent.py
│   ├── reconciliation_agent.py
│   ├── dispute_agent.py
│   └── form_agent.py
├── api/v1/
│   ├── b2b.py                     # B2B CaaS router
│   └── schemas.py
├── services/
│   ├── whatsapp_service.py
│   ├── gemini_service.py
│   ├── sarvam_service.py          # STT saarika:v2.5 / TTS bulbul:v2
│   ├── pdf_service.py
│   ├── esign_service.py           # Aadhaar eSign (demo mode)
│   └── form_overlay_service.py    # Form 5IF coordinate overlay
├── core/
│   ├── config.py
│   ├── database.py
│   ├── auth.py
│   └── celery_app.py
├── models/
├── migrations/
├── templates/                     # Jinja2 dashboard
├── Form5IF.pdf                    # Official EPFO template
└── docker-compose.yml
```

---

## License

MIT
