# AIShippingInspectAgent

Agentic AI Inspection System for shipping invoice review, fleet classification, policy retrieval, validation, human approval, notifications, and dashboard monitoring.

## Folder Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── workers/
│   ├── samples/
│   ├── scripts/
│   └── tests/
├── frontend/
│   ├── app/
│   ├── components/
│   └── lib/
├── docker-compose.yml
└── .env.example
```

## Setup

```bash
cp .env.example .env
docker compose up -d postgres redis

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python scripts/seed_policies.py
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

```bash
cd backend
source .venv/bin/activate
QUEUE_BACKEND=redis python scripts/seed_policies.py
python -m app.workers.redis_worker
```

```bash
cd backend
source .venv/bin/activate
pytest
```

## API

```text
POST /submit
GET  /jobs
GET  /jobs/{id}
POST /review/{id}
GET  /metrics
```
