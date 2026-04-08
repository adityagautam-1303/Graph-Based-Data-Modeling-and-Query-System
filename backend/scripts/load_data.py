"""
Load JSONL data from sap-o2c-data into PostgreSQL (or SQLite for dev).
Cleans and normalizes data before ingestion.
"""
import json
import os
import glob
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
# Use SQLite if PostgreSQL not available (dev without DB)
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_SQLITE = False
if "postgresql" in DATABASE_URL:
    try:
        from sqlalchemy import create_engine
        e = create_engine(DATABASE_URL)
        with e.connect():
            pass
    except Exception:
        DATABASE_URL = "sqlite:///" + str(Path(__file__).resolve().parent.parent.parent / "o2c.db")
        USE_SQLITE = True
        print("PostgreSQL not available. Using SQLite:", DATABASE_URL)
else:
    USE_SQLITE = "sqlite" in DATABASE_URL


def load_jsonl_dir(path: str) -> pd.DataFrame:
    """Load all JSONL files from a directory into a single DataFrame."""
    files = glob.glob(os.path.join(path, "*.jsonl"))
    rows = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    rows.append(flatten_json(obj))
                except json.JSONDecodeError:
                    continue
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def flatten_json(obj: Any, parent_key: str = "") -> dict:
    """Flatten nested structures (e.g. creationTime: {hours, minutes, seconds})."""
    items = []
    skip_flatten = {"creationTime", "actualGoodsMovementTime"}
    for k, v in obj.items():
        new_key = f"{parent_key}_{k}" if parent_key else k
        if isinstance(v, dict) and (k in skip_flatten or len(v) <= 5):
            items.append((new_key, str(v) if v else None))
        elif isinstance(v, dict) and not any(
            isinstance(x, (dict, list)) for x in (v.values() or [])
        ):
            for k2, v2 in (v or {}).items():
                items.append((f"{new_key}_{k2}", v2))
        elif v is None or (isinstance(v, (list, dict)) and not v):
            items.append((new_key, None))
        else:
            items.append((new_key, v))
    return dict(items)


def clean_df(df: pd.DataFrame, _table: str) -> pd.DataFrame:
    """Clean DataFrame: handle nulls, types, duplicates."""
    if df.empty:
        return df
    df = df.drop_duplicates()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).replace("nan", "").replace("None", "").replace("<NA>", "")
        if "date" in col.lower() or "datetime" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except Exception:
                pass
    return df


def main():
    base = Path(__file__).resolve().parent.parent.parent / "sap-o2c-data"
    if not base.exists():
        print("sap-o2c-data folder not found. Extract dataset first.")
        return

    engine = create_engine(DATABASE_URL)

    if not USE_SQLITE:
        with engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS o2c"))
            conn.commit()

    tables_config = {
        "business_partners": "business_partners",
        "business_partner_addresses": "business_partner_addresses",
        "customer_company_assignments": "customer_company_assignments",
        "customer_sales_area_assignments": "customer_sales_area_assignments",
        "products": "products",
        "product_descriptions": "product_descriptions",
        "product_plants": "product_plants",
        "product_storage_locations": "product_storage_locations",
        "plants": "plants",
        "sales_order_headers": "sales_order_headers",
        "sales_order_items": "sales_order_items",
        "sales_order_schedule_lines": "sales_order_schedule_lines",
        "outbound_delivery_headers": "outbound_delivery_headers",
        "outbound_delivery_items": "outbound_delivery_items",
        "billing_document_headers": "billing_document_headers",
        "billing_document_items": "billing_document_items",
        "billing_document_cancellations": "billing_document_cancellations",
        "journal_entry_items_accounts_receivable": "journal_entry_items_accounts_receivable",
        "payments_accounts_receivable": "payments_accounts_receivable",
    }

    schema = "o2c" if not USE_SQLITE else None
    for table, folder in tables_config.items():
        path = base / folder
        if not path.exists():
            print(f"Skipping {folder} (not found)")
            continue
        print(f"Loading {folder}...")
        df = load_jsonl_dir(str(path))
        if df.empty:
            print(f"  No data in {folder}")
            continue
        df = clean_df(df, folder)
        df.columns = [c.replace("-", "_").replace(" ", "_")[:63] for c in df.columns]
        df.to_sql(
            table,
            engine,
            schema=schema,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=500,
        )
        print(f"  Loaded {len(df)} rows into {schema or 'main'}.{table}")

    if USE_SQLITE:
        print("Note: SQLite schema is 'main'. Set DATABASE_URL for PostgreSQL.")

    print("Done.")


if __name__ == "__main__":
    main()
