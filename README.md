# SmartDesk AI — Agentic ServiceNow Incident Triage

An AI-powered system that automatically detects, classifies, and assigns ServiceNow incidents using LangChain, ChromaDB, and OpenAI.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI Server                     │
│                                                     │
│  ┌──────────┐   ┌────────────┐   ┌──────────────┐  │
│  │ Poller / │──▶│ LangChain  │──▶│  Decision    │  │
│  │ Webhook  │   │ Agent      │   │  Engine      │  │
│  └──────────┘   └─────┬──────┘   └──────┬───────┘  │
│                       │                  │          │
│                 ┌─────▼──────┐    ┌──────▼───────┐  │
│                 │ ChromaDB   │    │ ServiceNow   │  │
│                 │ Embeddings │    │ Client       │  │
│                 └────────────┘    └──────────────┘  │
│                                                     │
│  ┌──────────┐   ┌────────────────────────────────┐  │
│  │ Feedback │   │ Dashboard (HTML/CSS/JS)         │  │
│  │ Store    │   └────────────────────────────────┘  │
│  └──────────┘                                       │
└─────────────────────────────────────────────────────┘
```

## Project Structure

```
SmartDesk AI/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, orchestrator, polling loop
│   ├── config.py             # Pydantic settings from .env
│   ├── models.py             # Data models (Incident, Classification, etc.)
│   ├── servicenow_client.py  # ServiceNow REST API client
│   ├── agent.py              # LangChain classification agent
│   ├── embedding_engine.py   # ChromaDB similarity engine
│   ├── decision_engine.py    # Confidence-based routing logic
│   ├── feedback.py           # Feedback loop persistence
│   └── logging_config.py     # Structured logging setup
├── static/
│   ├── style.css             # Dashboard styles
│   └── app.js                # Dashboard JavaScript
├── templates/
│   └── dashboard.html        # Live dashboard UI
├── tests/
│   ├── test_models.py
│   ├── test_decision_engine.py
│   └── test_api.py
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Quick Start

### 1. Clone & Install

```bash
cd "SmartDesk AI"
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
# Edit .env with your ServiceNow and OpenAI credentials
```

Required variables:
| Variable | Description |
|---|---|
| `SERVICENOW_INSTANCE_URL` | e.g. `https://dev12345.service-now.com` |
| `SERVICENOW_USERNAME` | ServiceNow API user |
| `SERVICENOW_PASSWORD` | ServiceNow API password |
| `OPENAI_API_KEY` | OpenAI API key |

### 3. Run

```bash
flask --app app.main:app run --port 8000 --debug
```

Open **http://localhost:8000** for the dashboard.

### 4. Docker

```bash
docker compose up --build
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Dashboard UI |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/recent` | Recently processed incidents |
| `GET` | `/api/stats` | Knowledge base & accuracy stats |
| `POST` | `/api/webhook` | Receive incident webhook from ServiceNow |
| `POST` | `/api/process` | Manually process a specific incident |
| `POST` | `/api/feedback` | Submit feedback on an assignment |
| `POST` | `/api/poll-now` | Trigger an immediate poll cycle |

## How It Works

1. **Detection** — Polls ServiceNow every 30s for incidents with `state=New`, or receives webhooks.
2. **Classification** — LangChain agent with GPT-4 analyzes the incident and returns category, severity, team, and confidence.
3. **Similarity Search** — ChromaDB finds similar historical incidents to validate/boost confidence.
4. **Decision** — Confidence thresholds drive action:
   - **≥ 80%** → Auto-assign to team
   - **50–79%** → Suggest assignment (requires approval)
   - **< 50%** → Route to fallback Service Desk queue
5. **Update** — Patches the ServiceNow incident with assignment group, priority, and detailed work notes.
6. **Feedback** — Manual corrections are captured and fed back into the embedding store.

## ServiceNow Setup

### Option A: Webhook (Preferred)

Create a **Business Rule** on the `incident` table:
- **When**: after insert
- **Script**: Send a REST message to `http://your-server:8000/api/webhook` with the incident fields.

### Option B: Polling (Default)

The system polls `/api/now/table/incident?sysparm_query=state=1` at the configured interval. No ServiceNow configuration needed.

## Testing

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

## Configuration Reference

All settings are in `.env`:

| Setting | Default | Description |
|---|---|---|
| `POLLING_INTERVAL_SECONDS` | `30` | How often to poll ServiceNow |
| `AUTO_ASSIGN_THRESHOLD` | `0.8` | Confidence for auto-assignment |
| `SUGGEST_THRESHOLD` | `0.5` | Confidence for suggestion |
| `OPENAI_MODEL` | `gpt-4` | LLM model to use |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | ChromaDB storage path |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
