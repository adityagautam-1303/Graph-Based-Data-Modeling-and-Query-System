# Order to Cash - Graph & Chat (Dodge AI)

A graph-based data modeling and natural language query system for the Order-to-Cash (O2C) business process. Built with PostgreSQL, LangChain, FastAPI, and React.

## Features

- **Graph Construction**: Relational data (Orders, Deliveries, Invoices, Journal Entries, Payments) converted into an interactive graph
- **Graph Visualization**: Force-directed graph with node inspection, expandable metadata
- **Conversational Query**: Natural language → SQL → data-backed answers via LangChain
- **Guardrails**: Restricts queries to the dataset domain; rejects off-topic prompts
- **Example Queries**: Products with most billing docs, trace flow, broken/incomplete flows

## Architecture

### Tech Stack

| Component | Technology |
|-----------|------------|
| Database | PostgreSQL (o2c schema) |
| Backend | FastAPI |
| LLM Pipeline | LangChain + Gemini/Groq (free tier) |
| Frontend | React + Vite + react-force-graph-2d |

### Data Flow

1. **Ingestion**: JSONL → cleaned → PostgreSQL (`o2c` schema)
2. **Graph**: SQL queries build nodes/edges from relational joins
3. **Chat**: User question → LangChain SQL Agent → PostgreSQL → LLM summarizes → Answer

### Database Schema

- `o2c.sales_order_headers`, `o2c.sales_order_items`
- `o2c.outbound_delivery_headers`, `o2c.outbound_delivery_items`
- `o2c.billing_document_headers`, `o2c.billing_document_items`
- `o2c.journal_entry_items_accounts_receivable`
- `o2c.payments_accounts_receivable`
- `o2c.business_partners`, `o2c.products`, `o2c.plants`

### LLM Prompting Strategy

- **System prompt** restricts scope to O2C dataset only
- **Schema context** provided for accurate SQL generation
- **Pre-routing**: Keyword-based off-topic detection before LLM call
- **Read-only**: Only SELECT queries executed

### Guardrails

- Off-topic detection (e.g., "write a poem", "translate")
- Response: *"This system is designed to answer questions related to the provided dataset only."*
- SQL restricted to SELECT; no DDL/DML

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

### 1. Database

**Option A - SQLite (no setup):** Use SQLite for quick start. Set in `backend/.env`:
```
DATABASE_URL=sqlite:///C:/path/to/your/project/o2c.db
```

**Option B - PostgreSQL:** Create a database and set `DATABASE_URL`:
```bash
createdb o2c_graph
```

### 2. Load Data

```bash
python backend/scripts/load_data.py
```
(If PostgreSQL is not running, the script auto-falls back to SQLite and creates `o2c.db` in the project root.)

### 3. Backend

```bash
pip install -r requirements.txt
cd backend
cp .env.example .env
# Edit .env: set DATABASE_URL and GOOGLE_API_KEY (or GROQ_API_KEY)
```

**LLM API Keys (free tier):**

- **Gemini**: https://ai.google.dev → Create API key
- **Groq**: https://console.groq.com → API Keys
- Set `GOOGLE_API_KEY` or `GROQ_API_KEY` in `.env`

### 4. Run Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Example Queries

1. **"Which products are associated with the highest number of billing documents?"**
2. **"91150187 - Find the journal entry number linked to this?"**
3. **"Trace the full flow of billing document 90504248"**
4. **"Identify sales orders that have delivered but not billed"**
5. **"Show me billing documents without delivery"**

## Project Structure

```
fde dodge ai/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI routes
│   │   ├── graph_service.py
│   │   └── sql_agent.py   # LangChain NL→SQL
│   └── scripts/
│       └── load_data.py
├── frontend/
│   └── src/
│       ├── App.tsx
│       ├── components/
│       │   ├── GraphPane.tsx
│       │   └── ChatSidebar.tsx
│       └── types.ts
├── sap-o2c-data/         # Extracted dataset
├── requirements.txt
└── README.md
```

## License

MIT
"# Graph-Based-Data-Modeling-and-Query-System" 
