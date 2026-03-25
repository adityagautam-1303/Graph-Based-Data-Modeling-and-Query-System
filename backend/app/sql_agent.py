"""
LangChain-based SQL pipeline: Natural language -> SQL -> data-backed answer.
Uses free-tier LLM (Gemini/Groq) with guardrails.
"""
import os
import re
from typing import Optional
from pathlib import Path

from sqlalchemy import text, create_engine
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

def _get_llm():
    if LLM_PROVIDER == "groq" and GROQ_API_KEY:
        return ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", api_key=GROQ_API_KEY, temperature=0)
    if GOOGLE_API_KEY:
        return ChatGoogleGenerativeAI(model="gemma-3-27b-it", google_api_key=GOOGLE_API_KEY, temperature=0)
    raise ValueError("Set GOOGLE_API_KEY or GROQ_API_KEY in .env.")

def _is_off_topic(query: str) -> bool:
    q = query.lower()
    block = ["write a poem", "write code", "translate", "explain physics", "who is", "what is the capital", "creative", "joke", "story", "recipe"]
    return any(b in q for b in block)

def get_sql_chain():
    schema = None if USE_SQLITE else "o2c"
    db = SQLDatabase.from_uri(DATABASE_URL, schema=schema, sample_rows_in_table_info=0, include_tables=[
        "sales_order_headers", "sales_order_items", "outbound_delivery_headers",
        "outbound_delivery_items", "billing_document_headers", "billing_document_items",
        "journal_entry_items_accounts_receivable", "payments_accounts_receivable",
        "business_partners", "products", "plants",
    ])
    llm = _get_llm()

    def get_schema(_):
        return db.get_table_info()

    prompt = ChatPromptTemplate.from_messages([
        ("system", DOMAIN_GUARDRAIL + "\n\n" + """YOU ARE AN SAP O2C EXPERT. Answer questions by writing SQL against raw tables.

RELATIONSHIP MAP (EXPLICIT):
1. SO <-> Delivery: soi."salesOrder" = odi."referenceSdDocument" AND CAST(soi."salesOrderItem" AS INTEGER) = CAST(odi."referenceSdDocumentItem" AS INTEGER)
2. Delivery <-> Billing: odi."deliveryDocument" = bdi."referenceSdDocument" AND CAST(odi."deliveryDocumentItem" AS INTEGER) = CAST(bdi."referenceSdDocumentItem" AS INTEGER)
3. Billing Header <-> Item: bdh."billingDocument" = bdi."billingDocument"
4. Billing <-> Journal: bdh."accountingDocument" = jei."accountingDocument"

RULES:
- ZERO HALLUCINATION (MANDATORY): You MUST use the EXACT ID provided in the question. The schema metadata does NOT contain the actual IDs. NEVER look for similar numbers.
- MANDATORY SELECT: In EVERY trace query, you MUST select soh.salesOrder, odh.deliveryDocument, bdh.billingDocument, and jei.accountingDocument for graph connectivity.
- JOIN: Use LEFT JOIN. Trace in either direction (SO -> Journal or Journal -> SO). 
- ITEM TABLES: ALWAYS join the ITEM tables (soi, odi, bdi) to bridge documents. Joins solely on headers often fail.
- ITEM SYNC: You MUST use CAST(col AS INTEGER) for all item columns to handle padding (e.g. '10' vs '000010').
- SQL ONLY: return ONLY SQL code block. No explanations.

SCHEMA: {schema}"""),
        MessagesPlaceholder(variable_name="history", optional=True),
        ("human", "{question}"),
    ])

    chain = (RunnablePassthrough.assign(schema=get_schema) | prompt | llm | StrOutputParser())
    return chain, db

def chain_invoke_summarizer(question: str, data: list):
    """
    Separate chain for data summarization using structured mappings.
    """
    llm = _get_llm()
    answer_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an AI assistant. The provided Data is the exact SQL result for the user's Question. You MUST include EVERY document identifier found in the Data in your final response, using the dictionary keys as labels (e.g. salesOrder: 123). Do NOT include item-level IDs (e.g. salesOrderItem, deliveryDocumentItem, referenceSdDocumentItem) in your answer as they are clutter. If the Data is empty, say 'I could not find a trace for this document'. NEVER make up examples. Do NOT use ** markdown formatting."),
        ("human", "Question: {question}\n\nData:\n{data}\n\nProvide a clear, data-backed answer."),
    ])
    answer_chain = answer_prompt | llm | StrOutputParser()
    return answer_chain.invoke({"question": question, "data": data}).replace("*", "").strip()

def query_natural_language(question: str, history: Optional[list] = None) -> dict:
    if _is_off_topic(question):
        return {"answer": "This system is designed to answer questions related to the O2C dataset only.", "sql": None, "data": None, "error": None}

    try:
        chain, db = get_sql_chain()
        messages = []
        if history:
            for h in history[-6:]:
                messages.append(HumanMessage(content=h.get("content", "")) if h.get("role") == "user" else AIMessage(content=h.get("content", "")))
        
        raw_sql = chain.invoke({"question": question, "history": messages}).strip()
        sql = re.sub(r'```sql|```', '', raw_sql).strip()
        
        # PostgreSQL camelCase fix
        if not USE_SQLITE:
            sql = re.sub(r'(?<!")\b([a-z]+[A-Z][a-zA-Z0-9]*)\b(?!")', r'"\1"', sql)
            sql = sql.replace("`", '"')

        data = []
        if sql.upper().startswith("SELECT") or sql.upper().startswith("WITH"):
            with db._engine.connect() as conn:
                res = conn.execute(text(sql))
                rows = res.mappings().fetchall()
                for r in rows:
                    data.append({k: str(v) if v is not None else None for k, v in r.items()})
        else:
            return {"answer": "Could not generate valid SQL.", "sql": sql, "data": None, "error": None}

        answer = chain_invoke_summarizer(question, data)
        
        if "trace" in question.lower() or "flow" in question.lower():
            answer += f"\n\n(Executed SQL: {sql})"
            
        return {"answer": answer, "sql": sql, "data": data, "error": None}
    except Exception as e:
        return {"answer": None, "sql": None, "data": None, "error": str(e)}
