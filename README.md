<div align="center">

<img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Flask-3.1+-000000?style=for-the-badge&logo=flask&logoColor=white" />
<img src="https://img.shields.io/badge/LangChain-0.3+-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" />
<img src="https://img.shields.io/badge/Gemini_2.0-8E75B2?style=for-the-badge&logo=google&logoColor=white" />
<img src="https://img.shields.io/badge/ChromaDB-FF6F00?style=for-the-badge&logo=databricks&logoColor=white" />
<img src="https://img.shields.io/badge/ServiceNow-62D84E?style=for-the-badge&logo=servicenow&logoColor=white" />
<img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />

<br/><br/>

# 🧠 SmartDesk AI

### Agentic IT Incident Triage & Resolution System

*Intelligent multi-agent system that automatically detects, classifies, assigns, and resolves ServiceNow incidents using LLM-powered agents, vector similarity search, and a knowledge base of resolution playbooks.*

<br/>

[Features](#-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [How It Works](#-how-it-works) · [API Reference](#-api-reference) · [Configuration](#%EF%B8%8F-configuration)

<br/>

---

</div>

<br/>

## ✨ Features

<table>
<tr>
<td width="50%">

### 🤖 Multi-Agent System
- **Classification Agent** — LLM-powered incident triage using Gemini 2.0 Flash with few-shot prompting
- **Resolver Agent** — Auto-generates step-by-step resolution guides from KB articles
- **Incident Generator** — Creates realistic test incidents targeting all 8 support teams

</td>
<td width="50%">

### 🧬 Vector Knowledge Base
- **25+ KB articles** covering Network, Security, IAM, Hardware, Database, Cloud, and more
- **ChromaDB** with cosine similarity for instant retrieval of relevant resolution playbooks
- **Self-learning** — every resolved incident enriches the knowledge base

</td>
</tr>
<tr>
<td width="50%">

### ⚡ Intelligent Routing
- **8 specialist teams** with configurable confidence thresholds
- **Auto-assign** (≥80%), **Suggest** (50-79%), or **Fallback** (<50%)
- **Round-robin** assignment within teams with lead escalation

</td>
<td width="50%">

### 📊 Live Dashboard
- Real-time incident feed with assignment status
- Expandable resolution guides with numbered steps
- Team breakdown, confidence meters, and accuracy tracking
- Dark/light theme with glassmorphism UI

</td>
</tr>
<tr>
<td width="50%">

### 🔄 ServiceNow Integration
- Bi-directional sync via REST API
- Auto-polls for new incidents every 30s
- Webhook support for real-time triggers
- Posts AI work notes + resolution steps to tickets

</td>
<td width="50%">

### 🎯 Feedback Loop
- Human-in-the-loop correction system
- Incorrect assignments feed back into embeddings
- Accuracy stats tracked and displayed on dashboard
- Continuous improvement over time

</td>
</tr>
</table>

<br/>

## 🏗 Architecture

```
                          ┌──────────────────────────────────────────────────┐
                          │              SmartDesk AI Server                 │
                          │                                                  │
  ┌─────────────┐        │  ┌────────────┐    ┌──────────────────────────┐  │
  │  ServiceNow │◄──────►│  │  Poller /  │───►│  🤖 Classification Agent │  │
  │  Instance   │        │  │  Webhook   │    │  (Gemini 2.0 + LangChain)│  │
  └─────────────┘        │  └────────────┘    └────────────┬─────────────┘  │
                          │                                 │                │
                          │                    ┌────────────▼─────────────┐  │
                          │                    │    ⚙️ Decision Engine     │  │
                          │                    │  (confidence thresholds) │  │
                          │                    └────────────┬─────────────┘  │
                          │                                 │                │
                          │  ┌────────────────┐ ┌──────────▼─────────────┐  │
                          │  │  🧬 ChromaDB    │ │  📋 Resolver Agent     │  │
                          │  │  Vector Store   │◄│  (KB → resolution      │  │
                          │  │  (25+ KB docs)  │ │   steps → work notes)  │  │
                          │  └────────────────┘ └────────────────────────┘  │
                          │                                                  │
                          │  ┌────────────────┐ ┌────────────────────────┐  │
                          │  │  📝 Feedback    │ │  🖥️ Dashboard           │  │
                          │  │  Store (JSONL)  │ │  (Flask + JS)          │  │
                          │  └────────────────┘ └────────────────────────┘  │
                          └──────────────────────────────────────────────────┘
```

### Agent Pipeline

```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────────┐    ┌──────────────┐
│ Incident │───►│ Similarity   │───►│ Classification│───►│ Decision       │───►│ Resolver     │
│ Detected │    │ Search       │    │ Agent (LLM)  │    │ Engine         │    │ Agent (LLM)  │
└──────────┘    │ (ChromaDB)   │    │              │    │                │    │              │
                │              │    │ • Category   │    │ • Auto-assign  │    │ • KB lookup  │
                │ • Top 5      │    │ • Severity   │    │ • Suggest      │    │ • Step-by-   │
                │   matches    │    │ • Team       │    │ • Fallback     │    │   step guide │
                │ • Resolution │    │ • Confidence │    │ • Priority     │    │ • Work notes │
                │   context    │    │ • Summary    │    │ • Assignee     │    │ • Escalation │
                └──────────────┘    └──────────────┘    └────────────────┘    └──────────────┘
```

<br/>

## 📁 Project Structure

```
SmartDesk AI/
├── app/
│   ├── __init__.py              # Package init
│   ├── main.py                  # Flask app, routes, orchestration pipeline
│   ├── config.py                # Pydantic settings from .env
│   ├── models.py                # Data models (Incident, Classification, Decision, etc.)
│   ├── agent.py                 # 🤖 Classification Agent (LangChain + Gemini)
│   ├── resolver_agent.py        # 📋 Resolver Agent (KB → resolution steps)
│   ├── embedding_engine.py      # 🧬 ChromaDB vector store & similarity search
│   ├── decision_engine.py       # ⚙️ Confidence-based routing & team roster
│   ├── servicenow_client.py     # 🔗 ServiceNow REST API client
│   ├── feedback.py              # 🎯 Feedback loop persistence
│   └── logging_config.py        # Structured logging (structlog)
├── data/
│   └── kb_articles.json         # 📚 25 KB articles with resolution playbooks
├── static/
│   ├── style.css                # Dashboard styles (glassmorphism, dark/light)
│   └── app.js                   # Dashboard JavaScript (real-time updates)
├── templates/
│   └── dashboard.html           # Live dashboard UI
├── chroma_data/                 # ChromaDB persistent storage
├── tests/
│   ├── test_models.py           # Model validation tests
│   ├── test_decision_engine.py  # Routing logic tests
│   └── test_api.py              # API endpoint tests
├── ingest_data.py               # Script to load KB articles into ChromaDB
├── run.py                       # Application entry point
├── setup_servicenow.py          # ServiceNow initial setup helper
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container image definition
├── docker-compose.yml           # Docker Compose config
└── .env                         # Environment variables (not committed)
```

<br/>

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **Google Cloud** project with Vertex AI API enabled
- **ServiceNow** developer instance ([get one free](https://developer.servicenow.com))

### 1️⃣ Clone & Install

```bash
git clone https://github.com/your-username/smartdesk-ai.git
cd smartdesk-ai

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2️⃣ Configure Environment

```bash
cp .env.example .env    # or: copy .env.example .env (Windows)
```

Edit `.env` with your credentials:

```env
# ServiceNow
SERVICENOW_INSTANCE_URL=https://devXXXXX.service-now.com
SERVICENOW_USERNAME=admin
SERVICENOW_PASSWORD=your-password

# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
GEMINI_MODEL=gemini-2.0-flash

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_data

# Thresholds
AUTO_ASSIGN_THRESHOLD=0.8
SUGGEST_THRESHOLD=0.5
POLLING_INTERVAL_SECONDS=30
```

### 3️⃣ Ingest Knowledge Base

```bash
python ingest_data.py
```

This loads 25 KB articles with resolution playbooks into ChromaDB.

### 4️⃣ Run

```bash
python run.py
```

Open **http://localhost:8000** — the dashboard is live.

### 🐳 Docker (Alternative)

```bash
docker compose up --build
```

<br/>

## 🔄 How It Works

<table>
<tr><td>

### Step 1 — Detection
The system polls ServiceNow every 30 seconds for incidents with `state=New` and no assignment group. Alternatively, a ServiceNow Business Rule can push incidents via webhook.

### Step 2 — Similarity Search
The incident description is embedded and compared against the ChromaDB vector store containing historical incidents and KB articles. Top 5 matches with resolution context are retrieved.

### Step 3 — Classification (Agent 1)
The **Classification Agent** (Gemini 2.0 Flash via LangChain) analyzes the incident with few-shot examples and similar incident context. It returns: category, subcategory, severity, assigned team, confidence score, and a summary.

### Step 4 — Decision Engine
Confidence thresholds determine the action:

| Confidence | Action | Behavior |
|:---:|:---:|:---|
| **≥ 80%** | `auto_assign` | Directly assigns to team + individual |
| **50–79%** | `suggest` | Suggests assignment, adds work note |
| **< 50%** | `fallback` | Routes to Service Desk queue |

### Step 5 — Resolution (Agent 2)
The **Resolver Agent** searches ChromaDB for relevant KB articles, then generates a tailored step-by-step resolution guide using the LLM. The guide is posted as a ServiceNow work note so the assignee has immediate actionable steps.

### Step 6 — Knowledge Enrichment
Every processed incident is stored back into ChromaDB, continuously enriching the knowledge base for future similarity searches.

### Step 7 — Feedback Loop
Analysts can mark assignments as correct or incorrect. Corrections are recorded and fed back into the embedding store, improving future routing accuracy.

</td></tr>
</table>

<br/>

## 👥 Support Teams

| Team | Handles | Lead |
|:---|:---|:---:|
| **Network Team** | VPN, DNS, firewall, Wi-Fi, connectivity | Alice Johnson |
| **Application Support** | App crashes, email, ERP, CRM, software bugs | Charlie Kim |
| **IAM Team** | Passwords, MFA, SSO, access requests, permissions | Ethan Brooks |
| **Security Team** | Phishing, malware, breaches, suspicious activity, SSL | Grace Lee |
| **Hardware Support** | Laptops, monitors, printers, peripherals | Isaac Turner |
| **Database Team** | DB errors, performance, backups, replication, SQL | Kevin Nakamura |
| **Cloud Infrastructure** | VMs, Kubernetes, storage, AWS/Azure/GCP, DevOps | Michael Okonkwo |
| **Service Desk** | General queries, onboarding, software requests | Oliver Grant |

<br/>

## 📋 Knowledge Base

The system ships with **25 pre-built KB articles** in `data/kb_articles.json`, each containing detailed resolution playbooks:

<details>
<summary><b>📂 View all KB articles</b></summary>

| ID | Title | Team |
|:---|:---|:---|
| KB0001 | VPN Connection Failure | Network Team |
| KB0002 | Network Printer Not Reachable | Network Team |
| KB0003 | DNS Resolution Failure | Network Team |
| KB0004 | Application Crashing on Launch | Application Support |
| KB0005 | Email Client Not Syncing | Application Support |
| KB0006 | Slow Application Performance | Application Support |
| KB0007 | Password Reset Request | IAM Team |
| KB0008 | Access Permission Request for Shared Drive | IAM Team |
| KB0009 | Multi-Factor Authentication Issue | IAM Team |
| KB0010 | Phishing Email Reported | Security Team |
| KB0011 | Malware Detected on Workstation | Security Team |
| KB0012 | Unauthorized Access Attempt Detected | Security Team |
| KB0013 | Laptop Hardware Failure | Hardware Support |
| KB0014 | Monitor Display Issues | Hardware Support |
| KB0015 | Database Connection Timeout | Database Team |
| KB0016 | Database Replication Lag | Database Team |
| KB0017 | Cloud VM Instance Not Responding | Cloud Infrastructure |
| KB0018 | Cloud Storage Bucket Access Denied | Cloud Infrastructure |
| KB0019 | New Employee Onboarding Setup | Service Desk |
| KB0020 | Software Installation Request | Service Desk |
| KB0021 | Wi-Fi Connectivity Dropping Intermittently | Network Team |
| KB0022 | ERP System Login Failure | Application Support |
| KB0023 | SSL Certificate Expiry Warning | Security Team |
| KB0024 | Kubernetes Pod CrashLoopBackOff | Cloud Infrastructure |
| KB0025 | Database Backup Failure | Database Team |

</details>

<br/>

## 📡 API Reference

| Method | Endpoint | Description |
|:---:|:---|:---|
| `GET` | `/` | Dashboard UI |
| `GET` | `/api/health` | Health check + KB size |
| `GET` | `/api/recent` | Recent processed & unassigned incidents |
| `GET` | `/api/stats` | Knowledge base size + accuracy metrics |
| `GET` | `/api/config` | Current configuration values |
| `GET` | `/api/teams` | Team roster with assignment counts |
| `PUT` | `/api/config` | Update thresholds, polling, model |
| `POST` | `/api/create-incident` | Auto-generate 5 test incidents via LLM |
| `POST` | `/api/assign-incident` | Trigger AI classification + assignment |
| `POST` | `/api/resolve` | Generate resolution steps for assigned ticket |
| `POST` | `/api/webhook` | Receive ServiceNow webhook payload |
| `POST` | `/api/process` | Manually process a specific incident |
| `POST` | `/api/feedback` | Submit feedback on assignment accuracy |
| `POST` | `/api/poll-now` | Trigger immediate ServiceNow poll |

<br/>

## ⚙️ Configuration

All settings are managed via environment variables (`.env`):

| Variable | Default | Description |
|:---|:---:|:---|
| `SERVICENOW_INSTANCE_URL` | — | ServiceNow instance base URL |
| `SERVICENOW_USERNAME` | — | ServiceNow API username |
| `SERVICENOW_PASSWORD` | — | ServiceNow API password |
| `GOOGLE_CLOUD_PROJECT` | — | GCP project ID for Vertex AI |
| `GOOGLE_CLOUD_LOCATION` | `global` | GCP region |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | ChromaDB storage path |
| `POLLING_INTERVAL_SECONDS` | `30` | ServiceNow poll interval |
| `AUTO_ASSIGN_THRESHOLD` | `0.8` | Confidence for auto-assignment |
| `SUGGEST_THRESHOLD` | `0.5` | Confidence for suggestion |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

<br/>

## 🔌 ServiceNow Setup

### Option A: Webhook (Recommended)

Create a **Business Rule** on the `incident` table:
- **When**: After insert
- **Condition**: `state == New`
- **Script**: POST incident fields to `http://your-server:8000/api/webhook`

### Option B: Polling (Default)

No ServiceNow configuration needed. The system automatically polls for new unassigned incidents at the configured interval.

<br/>

## 🧪 Testing

```bash
pip install pytest
pytest tests/ -v
```

<br/>

## 🛠 Tech Stack

| Component | Technology |
|:---|:---|
| **Backend** | Python 3.12, Flask |
| **LLM** | Google Gemini 2.0 Flash (Vertex AI) |
| **Agent Framework** | LangChain 0.3 |
| **Vector Database** | ChromaDB (all-MiniLM-L6-v2 embeddings) |
| **ITSM Platform** | ServiceNow (REST API) |
| **Frontend** | Vanilla JS, CSS (glassmorphism) |
| **Logging** | structlog (structured JSON) |
| **Containerization** | Docker, Docker Compose |

<br/>

<div align="center">

---

**Built with ❤️ and AI agents**

*SmartDesk AI — Because every incident deserves an intelligent response.*

</div>
