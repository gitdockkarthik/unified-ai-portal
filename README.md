# Unified AI Portal

A single portal with two AI-powered analysis agents built on FastAPI, Claude, DuckDB, and PostgreSQL.

## Agents

| Agent | Purpose | Colour |
|-------|---------|--------|
| 💰 CUR Analyser | AWS Cost & Usage Report analysis | Blue (#4F8EF7) |
| 🚨 Alert Analyser | OpsGenie alert noise detection | Red (#DC3545) |

## Quick Start

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

docker compose up --build
```

Frontend: http://localhost:8000  
API Docs: http://localhost:8000/docs

## Project Structure

```
unified-ai-portal/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── main.py              # FastAPI unified router
│   ├── database.py          # Async SQLAlchemy
│   ├── models.py            # ORM models
│   ├── schemas.py           # Pydantic schemas
│   ├── shared/
│   │   └── claude_base.py   # Shared Claude client
│   └── agents/
│       ├── cur/             # CUR Analyser agent
│       │   ├── routes.py
│       │   ├── engine.py    # DuckDB query engine
│       │   └── claude.py    # Cost analysis AI
│       └── alerts/          # Alert Analyser agent
│           ├── routes.py
│           ├── engine.py
│           ├── noise_detector.py  # Noise classification
│           └── claude.py    # Alert analysis AI
├── frontend/
│   ├── index.html           # Home / portal overview
│   ├── style.css            # Shared design system
│   ├── portal.js            # Shared utilities
│   ├── agents/
│   │   ├── cur/             # CUR pages (chat, dashboard, reports, settings)
│   │   └── alerts/          # Alert pages (chat, dashboard, reports, settings)
│   └── admin/
│       └── index.html
└── db/
    └── init.sql
```

## CUR Analyser

- Upload AWS CUR CSV files
- DuckDB powers instant in-memory SQL queries
- Claude analyses cost trends, identifies waste
- Dashboard: total cost, top services, daily trend
- Chatbot: natural language AWS cost questions

## Alert Analyser

### Noise Detection Logic

**Noise indicators:**
- Same alert fires >3× within 1 hour
- Auto-resolves within 5 minutes with no acknowledgement
- Source has >70% auto-resolve rate
- Alert fires repeatedly (count >5)

**Genuine indicators:**
- Open >30 minutes
- Human acknowledged
- P1 or P2 priority
- First occurrence

### Dashboard Tabs
1. **Overview** — total/noise/genuine counts, donut chart, daily trend
2. **Noise Analysis** — top noisy sources, repeat offenders, suppression recommendations
3. **Genuine Alerts** — high severity table, unresolved, team breakdown
4. **Trend Analysis** — hourly heatmap, peak times, service health score

### Chatbot Questions
- "Which service generates the most noise?"
- "What is our noise-to-signal ratio?"
- "Which alerts should we suppress?"
- "Show me genuine P1 alerts"
- "What time of day do most alerts fire?"

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cur/reports/upload` | POST | Upload CUR CSV |
| `/api/cur/dashboard/latest/data` | GET | Latest dashboard data |
| `/api/cur/chat` | POST | CUR chatbot |
| `/api/alerts/reports/generate` | POST | Generate synthetic alerts |
| `/api/alerts/reports/upload` | POST | Upload OpsGenie JSON |
| `/api/alerts/dashboard/latest/data` | GET | Alert dashboard data |
| `/api/alerts/chat` | POST | Alert chatbot |
| `/api/agents` | GET | List all agents |
| `/api/health` | GET | Health check |

## Deployment (Railway)

1. Create new Railway project
2. Add PostgreSQL service
3. Set `ANTHROPIC_API_KEY` environment variable
4. Set `DATABASE_URL` to Railway PostgreSQL URL (use `postgresql+asyncpg://...`)
5. Deploy backend with root directory: `backend`
6. Deploy frontend as static service with root: `frontend`

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `DATABASE_URL` | Yes | PostgreSQL connection string |

## Phase Roadmap

| Phase | Status | Features |
|-------|--------|---------|
| Phase 1 | ✅ Active | File upload, synthetic data, AI chatbot, dashboards |
| Phase 2 | 🔜 Coming | Live API feeds (OpsGenie, PagerDuty, Datadog, CloudWatch) |
| Phase 3 | 🔜 Coming | Escalations (Slack, Teams, Email) |
