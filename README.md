# GhostWriter AI (Haqdaar)

> WhatsApp-first agentic system that helps Indian families file post-death EPF and insurance claims — with multilingual voice support, document quality checks, and auto-generated government forms.

---

## What It Does

When a breadwinner dies, the family must file claims across EPF, EDLI insurance, state pension schemes, and more. The process requires multiple forms, document verification, and compliance checks — typically taking months with a lawyer. Haqdaar does this over WhatsApp in under 10 minutes.

The user sends a message. The system:
1. Guides them through onboarding questions in their language (Telugu, Hindi, or English)
2. Sends voice notes at every step using Sarvam TTS
3. Verifies uploaded documents using Gemini Vision
4. Discovers all eligible schemes and calculates total entitlement
5. Runs a 100-point compliance audit
6. Generates and delivers the official EPFO Form 5(IF) pre-filled with all their details

---

## Project Status

| Feature | Status |
| :--- | :--- |
| WhatsApp webhook (Meta Cloud API) | Live |
| Multilingual onboarding flow | Live — Telugu, Hindi, English |
| Voice notes via Sarvam TTS | Live — OGG Opus for WhatsApp |
| Document QualityAgent (Gemini Vision) | Live — 6-point pre-flight check |
| EntitlementAgent | Live — EPF, EDLI, PMJJBY, state schemes |
| ComplianceAgent (100-point audit) | Live |
| Form5IF overlay (official EPFO template) | Live — pre-filled PDF delivered over WhatsApp |
| EPF Form 20 fallback | Live |
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
| FormAgent | Overlays family data onto official Form5IF.pdf template; falls back to ReportLab Form 20 |

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| Backend | FastAPI (async Python) |
| LLM | Google Gemini 2.5 Flash |
| STT / TTS / Translation | Sarvam AI (Indian language optimized) |
| Messaging | Meta WhatsApp Cloud API v18 |
| Database | PostgreSQL via async SQLAlchemy |
| Migrations | Alembic |
| Task queue | Celery + Redis |
| PDF generation | ReportLab + pypdf overlay |
| Audio | pydub + FFmpeg (WAV to OGG Opus) |
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
                          |
          ┌───────────────┼───────────────┐
          v               v               v
    GriefAgent      OnboardingFlow    B2B API (/api/v1/b2b)
                          |
          ┌───────────────┼───────────────┐
          v               v               v
   QualityAgent   EntitlementAgent  ComplianceAgent
                          |
                    FormAgent (Form5IF overlay)
                          |
                    PDF delivered over WhatsApp
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
```

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
│   ├── sarvam_service.py
│   ├── pdf_service.py
│   └── form_overlay_service.py    # Form5IF coordinate overlay
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
