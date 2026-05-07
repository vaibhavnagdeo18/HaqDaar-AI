# 🖋️ GhostWriter AI (Haqdaar)

![GhostWriter Hero Image](file:///Users/vaibhavnagdeo/.gemini/antigravity/brain/847e99ca-c542-4c51-abe3-c6932fbeb565/ghostwriter_hero_image_1777959252095.png)

> **Empowering Indian families to navigate the complex post-death claims process with a WhatsApp-first, multilingual agentic AI system.**

---

## 🌟 Overview

**GhostWriter AI** (also known as **Haqdaar**) is a specialized agentic system designed to simplify the daunting task of filing post-death claims for Indian families. Dealing with the loss of a loved one is hard enough; navigating the bureaucracy of EPF, insurance, and government schemes shouldn't be. 

Our system provides a seamless, empathetic interface via WhatsApp, supporting multiple Indian languages through voice and text. It uses a swarm of specialized AI agents to discover entitlements, analyze document quality, audit for compliance, and generate real claim forms automatically.

---

## 📊 Project Status

| Feature | Status | Notes |
| :--- | :--- | :--- |
| **Entitlement Agent** | ✅ Functional | Core discovery logic active (EPF, State Schemes) |
| **Dispute Agent** | ✅ Functional | Objection letter drafting active |
| **Quality Agent** | ✅ Functional | Document clarity and type detection |
| **Compliance Agent** | ✅ Functional | 100-point audit scoring (Task 2) |
| **Reconciliation Agent**| ✅ Functional | Identity mismatch analysis & affidavit gen (Task 3) |
| **PDF Generation** | ✅ Functional | Automatic EPF Form 20 & Claim Letter (Task 1/4) |
| **Admin Dashboard UI** | ✅ Functional | Live Case tracking at `/dashboard` (Task 6) |
| **Voice Notes (TTS)** | ✅ Functional | OGG Opus conversion for WhatsApp delivery (Task 1) |
| **PostgreSQL Persistence**| ✅ Functional | Full state machine persistence (Task 5) |
| **Celery Alerts** | ✅ Functional | Daily 9 AM IST deadline notifications (Task 7) |

---

## 🤖 The Agentic Swarm

GhostWriter AI is powered by a team of specialized agents, each focused on a critical part of the claims lifecycle:

*   **🔍 Entitlement Agent**: Analyzes user demographics and employment history to discover eligible government and private schemes.
*   **⚖️ Dispute Agent**: When a claim is denied, this agent analyzes the denial letter and drafts precise, legal-grade objection letters.
*   **📋 Quality Agent**: Instantly assesses the quality of uploaded documents to ensure they are legible and complete.
*   **🛡️ Compliance Agent**: Runs a 100-point audit on family data, automatically triggering form generation once all criteria are met.
*   **🤝 Reconciliation Agent**: Detects identity mismatches (e.g., Aadhaar vs. Death Certificate) and drafts "One-and-the-Same" person affidavits.
*   **📝 Form Agent**: Maps collected family data to official templates (like EPF Form 20) and generates ready-to-submit PDFs.

### 🎙️ Multilingual WhatsApp First
*   **Native Language Support**: Full support for Hindi, Telugu, and English.
*   **Voice Interaction**: Send voice notes and receive audio responses (transcoded to OGG Opus for perfect WhatsApp playback).
*   **Automatic Deadlines**: Receive daily reminders about claim deadlines (30 days/7 days/24 hours) via Celery Beat.

---

## 🛠️ Tech Stack

*   **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
*   **LLM & Reasoning**: [Google Gemini Pro](https://deepmind.google/technologies/gemini/)
*   **STT/TTS/Translation**: [Sarvam AI](https://www.sarvam.ai/) (Optimized for Indian Languages)
*   **Database**: [PostgreSQL](https://www.postgresql.org/) (Async SQLAlchemy)
*   **Task Queue**: [Redis](https://redis.io/) & [Celery](https://docs.celeryq.dev/)
*   **Document Generation**: [ReportLab](https://www.reportlab.com/) (PDF Gen)
*   **Audio**: [pydub](https://github.com/jiaaro/pydub) & [FFmpeg](https://ffmpeg.org/) (WAV to OGG Opus)
*   **Dashboard**: Jinja2 & Tailwind CSS

---

## 🏗️ Architecture

```mermaid
graph TD
    User((User)) -- WhatsApp/Voice --> WA[WhatsApp Service]
    WA -- Webhook --> API[FastAPI App]
    
    subgraph "Agentic Swarm (Gemini Powered)"
        API --> EA[Entitlement Agent]
        API --> DA[Dispute Agent]
        API --> QA[Quality Agent]
        API --> CA[Compliance Agent]
        API --> RA[Reconciliation Agent]
        API --> FA[Form Agent]
    end
    
    API --> DB[(PostgreSQL)]
    API --> RD[Redis/Celery]
    RD --> BEAT[Celery Beat: Deadline Alerts]
    
    API --> Sarvam[Sarvam AI: STT/TTS/Translation]
    API --> PDF[PDF Service: Form 20/Affidavits]
    
    API --> Dash[Admin Dashboard UI: /dashboard]
```

---

## 🚀 Getting Started

### Prerequisites
*   Docker and Docker Compose
*   FFmpeg (included in Dockerfile)
*   API Keys for Gemini, Sarvam, and Meta WhatsApp Business.

### Setup & Run
1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/ghostwriter.git
    cd ghostwriter
    ```

2.  **Configure environment**:
    ```bash
    cp .env.example .env
    # Fill in your GOOGLE_API_KEY, SARVAM_API_KEY, and WHATSAPP tokens
    ```

3.  **Start the system**:
    ```bash
    docker-compose up --build
    ```

4.  **Simulate a Journey**:
    ```bash
    ./demo_test.sh
    ```
    This script will simulate a full user journey from onboarding to PDF generation.

5.  **Monitor Cases**:
    Visit `http://localhost:8000/dashboard` to view live case statuses and compliance scores.

---

## 📂 Project Structure

```text
ghostwriter/
├── main.py                  # Entry point, API Webhooks & State Machine
├── agents/                  # Specialized Gemini-powered Agents
├── core/                    # Database, Celery, and App Configuration
├── services/                # WhatsApp, Sarvam, Gemini & PDF Services
├── models/                  # SQLAlchemy Database Models
├── templates/               # Jinja2 Dashboard Templates
├── demo_test.sh             # Full E2E Integration Test Script
└── docker-compose.yml       # Infrastructure Orchestration
```

---

## 📄 License

This project is licensed under the MIT License.

---

<p align="center">
  Built with ❤️ for the resilient families of India.
</p>
