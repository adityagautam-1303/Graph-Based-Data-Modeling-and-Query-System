"""
LangChain-based SQL pipeline: Natural language -> SQL -> data-backed answer.
Uses free-tier LLM (Gemini/Groq) with guardrails.
"""
import os
from typing import Optional
from pathlib import Path

from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None  # Optional dependency
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/o2c_graph")
USE_SQLITE = "sqlite" in DATABASE_URL
if not USE_SQLITE:
    try:
        from sqlalchemy import create_engine
        e = create_engine(DATABASE_URL)
        with e.connect():
            pass
    except Exception:
        _p = Path(__file__).resolve().parent.parent.parent / "o2c.db"
        DATABASE_URL = f"sqlite:///{_p}"
        USE_SQLITE = True
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

DOMAIN_GUARDRAIL = """You MUST only answer questions about the Order-to-Cash (O2C) dataset.
The dataset contains: Sales Orders, Deliveries, Billing Documents, Journal Entries, Payments, Customers, Products, Plants.
If the user asks about anything else (general knowledge, creative writing, code, unrelated topics), respond EXACTLY:
"This system is designed to answer questions related to the provided dataset only. Please ask about Orders, Deliveries, Invoices, Payments, Customers, or Products."
Do not attempt to answer off-topic questions."""

SCHEMA_CONTEXT = """
O2C TRACING LOGIC (CRITICAL):
- Billing -> Delivery: `billing_document_items."referenceSdDocument"` = `outbound_delivery_headers."deliveryDocument"`
- Delivery -> SalesOrder: `outbound_delivery_items."referenceSdDocument"` = `sales_order_headers."salesOrder"`
- Billing -> JournalEntry: `billing_document_headers."billingDocument"` = `journal_entry_items_accounts_receivable."referenceDocument"`
PostgreSQL schema is 'o2c'. Use double quotes for camelCase columns.
"""

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def _get_llm():
    if LLM_PROVIDER == "groq" and GROQ_API_KEY:
        return ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", api_key=GROQ_API_KEY, temperature=0)
    if LLM_PROVIDER == "openrouter" and OPENROUTER_API_KEY and ChatOpenAI:
        return ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
            model="qwen/qwen3-next-80b-a3b-instruct:free",
            temperature=0
        )
    if LLM_PROVIDER == "openai" and OPENAI_API_KEY and ChatOpenAI:
        return ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY, temperature=0)
    if GOOGLE_API_KEY:
        return ChatGoogleGenerativeAI(model="gemma-3-27b-it", google_api_key=GOOGLE_API_KEY, temperature=0)
    raise ValueError(
        "Set GOOGLE_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY in .env. "
        "Gemini offers a free tier: https://ai.google.dev"
    )

def _is_off_topic(query: str) -> bool:
    q = query.lower()
    block = [
        "write a poem", "write code", "translate", "summarize", "explain physics",
        "who is", "what is the capital", "general knowledge", "creative",
        "joke", "story", "recipe", "how to cook", "weather", "sports",
    ]
    return any(b in q for b in block)

def get_sql_chain():
    schema = None if USE_SQLITE else "o2c"
    # NOTE: We MUST restrict tables here because some SAP tables (like business_partner_addresses) 
    # contain "infinity" dates (9999-12-31) which crash the LangChain sampler.
    db = SQLDatabase.from_uri(DATABASE_URL, schema=schema, sample_rows_in_table_info=1, include_tables=[
        "sales_order_headers", "sales_order_items", "outbound_delivery_headers",
        "outbound_delivery_items", "billing_document_headers", "billing_document_items",
        "journal_entry_items_accounts_receivable", "payments_accounts_receivable",
        "business_partners", "products", "plants",
    ])
    llm = _get_llm()

    def get_schema(_):
        return db.get_table_info() # sample_rows_in_table_info=1 ensures we see doc ID formats!

    prompt = ChatPromptTemplate.from_messages([
        ("system", DOMAIN_GUARDRAIL + "\n\n" + """YOU ARE AN SAP DATA EXPERT.
Your goal is to write SQL queries against raw SAP tables to answer business questions (e.g. tracing flows).

SAP O2C FIELD SEMANTICS (CRITICAL ALIASES):
- `billing_document_items"."referenceSdDocument"` IS THE `deliveryDocument` ID.
- `outbound_delivery_items"."referenceSdDocument"` IS THE `salesOrder` ID.
- `journal_entry_items_accounts_receivable"."referenceDocument"` IS THE `billingDocument` ID.
- `journal_entry_items_accounts_receivable"."accountingDocument"` IS THE `journalEntry` ID.

SAP O2C RELATIONSHIP MAP:
1. `sales_order_headers` (Head) -> `outbound_delivery_items` (on `salesOrder` = `referenceSdDocument`)
2. `outbound_delivery_headers` (Head) -> `outbound_delivery_items` (on `deliveryDocument` = `deliveryDocument`)
3. `outbound_delivery_headers` (Head) -> `billing_document_items` (on `deliveryDocument` = `referenceSdDocument`)
4. `billing_document_headers` (Head) -> `billing_document_items` (on `billingDocument` = `billingDocument`)
5. `billing_document_headers` (Head) -> `journal_entry_items_accounts_receivable` (on `billingDocument` = `referenceDocument`)

RULES:
- When asked for a "trace" or "flow", use `LEFT JOIN` to traverse all headers and select all document IDs.
- For each document, select its primary identifier (e.g. `salesOrder`, `deliveryDocument`, `billingDocument`, `accountingDocument`).
- Use table aliases. Wrap camelCase columns in double quotes. Prefix with 'o2c' schema.
- Return ONLY the SQL. No explanation. No markdown.
- Wrap numeric ID strings in single quotes (e.g. '91150206').

DATABASE SCHEMA:
{schema}"""),
        MessagesPlaceholder(variable_name="history", optional=True),
        ("human", "{question}"),
    ])

    chain = (
        RunnablePassthrough.assign(schema=get_schema)
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain, db


def query_natural_language(
    question: str,
    history: Optional[list] = None,
) -> dict:
    """
    Convert natural language to SQL, execute, and return data-backed answer.
    """
    if _is_off_topic(question):
        return {
            "answer": "This system is designed to answer questions related to the provided dataset only. Please ask about Orders, Deliveries, Invoices, Payments, Customers, or Products.",
            "sql": None,
            "data": None,
            "error": None,
        }

    try:
        chain, db = get_sql_chain()
        messages = []
        if history:
            for h in history[-6:]:
                if h.get("role") == "user":
                    messages.append(HumanMessage(content=h.get("content", "")))
                elif h.get("role") == "assistant":
                    messages.append(AIMessage(content=h.get("content", "")))
        inp = {"question": question, "history": messages}
        raw = chain.invoke(inp)

        if "This system is designed to answer" in raw:
            return {
                "answer": raw.strip(),
                "sql": None,
                "data": None,
                "error": None,
            }

        import re
        sql = raw.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()

        # Forcibly double-quote any unquoted camelCase words to fix Postgres case-folding
        if not USE_SQLITE:
            sql = re.sub(r'(?<!")\b([a-z]+[A-Z][a-zA-Z0-9]*)\b(?!")', r'"\1"', sql)

        if sql.upper().startswith("SELECT") or sql.upper().startswith("WITH"):
            sql = sql.replace("`", '"')
            result = db.run(sql)
            rows = _parse_result(result)
            llm = _get_llm()
            answer_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an AI assistant. The provided Data is the exact SQL result for the user's Question. You MUST include EVERY document identifier found in the Data in your final response. If the Data is empty, say 'I could not find a trace for this document in the actual data'. NEVER make up hypothetical examples or use placeholders like 'Sales Order 123'. Do NOT use ** markdown formatting."),
                ("human", "Question: {question}\n\nData:\n{data}\n\nProvide a clear, data-backed answer containing all specific identifiers from the Data."),
            ])
            answer_chain = answer_prompt | llm | StrOutputParser()
            answer = answer_chain.invoke({"question": question, "data": result}).replace("*", "").strip()
            
            # Append SQL for trace debugging
            if "trace" in question.lower() or "flow" in question.lower():
                 answer += f"\n\n(Executed SQL: {sql})"
                 
            return {"answer": answer, "sql": sql, "data": rows, "error": None}
        else:
            return {"answer": "I could not generate a valid query for that question.", "sql": sql, "data": None, "error": None}
    except Exception as e:
        return {
            "answer": f"I encountered an error: {str(e)}. Please try rephrasing your question.",
            "sql": None,
            "data": None,
            "error": str(e),
        }


def _parse_result(result: str) -> list:
    """Parse raw SQL output string into a list of row values."""
    if not result:
        return []
    rows = []
    # result is normally a string representation of a list of tuples like "[(val1, val2), ...]"
    # but db.run() context can sometimes look like a table
    lines = result.split("\n")
    for line in lines:
        if "|" in line:
            # Table format extraction
            if line.strip().startswith("-") or "+-" in line:
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts:
                rows.append(parts)
        elif "(" in line and ")" in line:
            # Tuple format extraction (default SQLAlchemy string)
            # Remove parentheses and split on commas that aren't inside quotes
            # (Crude but usually works for simple O2C IDs)
            content = line.strip().strip("[](),")
            if content:
                rows.append([p.strip().strip("'\"") for p in content.split(",")])
    
    return rows[:50]
