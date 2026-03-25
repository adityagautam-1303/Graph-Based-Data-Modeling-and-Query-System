"""
Graph construction from PostgreSQL relational data.
Builds nodes and edges for the Order-to-Cash flow.
"""
import os
from typing import Optional
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/o2c_graph")

# SQLite fallback when PostgreSQL unavailable
_db_path = str(Path(__file__).resolve().parent.parent.parent / "o2c.db")
if "sqlite" not in DATABASE_URL:
    try:
        e = create_engine(DATABASE_URL)
        with e.connect():
            pass
    except Exception:
        DATABASE_URL = f"sqlite:///{_db_path}"

if "sqlite" in DATABASE_URL:
    SCHEMA = ""
    TABLE_PREFIX = ""
else:
    SCHEMA = "o2c"
    TABLE_PREFIX = "o2c."

def get_engine():
    return create_engine(DATABASE_URL)

def build_graph(
    limit: int = 50000,
    focus_entity: Optional[str] = None,
    focus_id: Optional[str] = None,
) -> dict:
    """
    Build a graph with nodes and edges from the O2C data.
    """
    engine = get_engine()
    nodes = []
    edges = []
    node_ids = set()

    def get_val(row, key, default=""):
        """Case-insensitive row access for any database row type (dict, Row, RowMapping)."""
        # Handle dicts and RowMappings (both have .keys())
        if hasattr(row, 'keys'):
            try:
                # Direct match first (case-sensitive)
                if key in row: return row[key]
                # Then case-insensitive match
                lk = key.lower()
                for k in row.keys():
                    if str(k).lower() == lk: return row[k]
            except Exception: pass
        # Handle legacy SQLAlchemy Row objects (which have _mapping)
        if hasattr(row, "_mapping"):
            m = row._mapping
            if key in m: return m[key]
            for mk in m.keys():
                if str(mk).lower() == key.lower(): return m[mk]
        return default

    def add_node(node_id: str, label: str, entity_type: str, data: dict):
        if not node_id: return
        if node_id in node_ids: return
        node_ids.add(node_id)
        # Normalize data for JSON safety
        clean_data = {str(k): (str(v) if v is not None else "") for k, v in (data or {}).items()}
        nodes.append({
            "id": str(node_id),
            "label": str(label),
            "entity": str(entity_type),
            "data": clean_data,
        })

    def add_edge(src: str, tgt: str, rel: str):
        if src in node_ids and tgt in node_ids:
            edges.append({"source": src, "target": tgt, "relation": rel})

    with engine.connect() as conn:
        # 1. Customers
        bp = conn.execute(
            text(f"SELECT * FROM {TABLE_PREFIX}business_partners LIMIT :lim"),
            {"lim": limit},
        ).mappings().fetchall()
        for r in bp:
            cid = get_val(r, 'customer')
            if cid:
                nid = f"BP-{cid}"
                name = get_val(r, 'businessPartnerName') or cid
                add_node(nid, f"Customer {name}", "Customer", r)

        # 2. Products
        prod = conn.execute(
            text(f"SELECT * FROM {TABLE_PREFIX}products LIMIT :lim"),
            {"lim": limit},
        ).mappings().fetchall()
        for r in prod:
            pid = get_val(r, 'product')
            if pid:
                add_node(f"P-{pid}", f"Product {pid}", "Product", r)

        # 3. Plants
        plant_rows = conn.execute(
            text(f"SELECT * FROM {TABLE_PREFIX}plants LIMIT :lim"),
            {"lim": limit},
        ).mappings().fetchall()
        for r in plant_rows:
            pl_id = get_val(r, 'plant')
            if pl_id:
                name = get_val(r, 'plantName') or pl_id
                add_node(f"PL-{pl_id}", f"Plant {name}", "Plant", r)

        # 4. Sales Orders
        so = conn.execute(
            text(f"SELECT * FROM {TABLE_PREFIX}sales_order_headers LIMIT :lim"),
            {"lim": limit},
        ).mappings().fetchall()
        for r in so:
            so_id = get_val(r, 'salesOrder')
            if so_id:
                nid = f"SO-{so_id}"
                add_node(nid, f"Sales Order {so_id}", "Sales Order", r)
                sold_to = get_val(r, 'soldToParty')
                if sold_to:
                    add_edge(f"BP-{sold_to}", nid, "PLACES_ORDER")

        # 5. Sales Order Items -> Products (USE QUOTES FOR POSTGRES CROSS-COMPAT)
        soi = conn.execute(
            text(f"""
                SELECT DISTINCT soh."salesOrder", soi.material
                FROM {TABLE_PREFIX}sales_order_items soi
                JOIN {TABLE_PREFIX}sales_order_headers soh ON soh."salesOrder" = soi."salesOrder"
                ORDER BY 1
            """)
        ).fetchall()
        for r in soi:
            if r[0] and r[1]:
                add_node(f"P-{r[1]}", f"Product {r[1]}", "Product", {"product": r[1]})
                add_edge(f"SO-{r[0]}", f"P-{r[1]}", "CONTAINS_ITEM")

        # 6. Deliveries
        odh = conn.execute(
            text(f"SELECT * FROM {TABLE_PREFIX}outbound_delivery_headers")
        ).mappings().fetchall()
        for r in odh:
            del_id = get_val(r, 'deliveryDocument')
            if del_id:
                nid = f"D-{del_id}"
                add_node(nid, f"Delivery {del_id}", "Delivery", r)
                ship_point = get_val(r, 'shippingPoint')
                if ship_point:
                    add_node(f"PL-{ship_point}", f"Plant {ship_point}", "Plant", {"plant": ship_point})
                    add_edge(nid, f"PL-{ship_point}", "SHIPPED_FROM")

        # 7. Delivery Items -> Sales Orders (USE QUOTES)
        odi = conn.execute(
            text(f"""
                SELECT DISTINCT "deliveryDocument", "referenceSdDocument"
                FROM {TABLE_PREFIX}outbound_delivery_items
                WHERE "referenceSdDocument" IS NOT NULL AND "referenceSdDocument" != ''
                ORDER BY 1
            """)
        ).fetchall()
        for r in odi:
            if r[0] and r[1]:
                add_edge(f"D-{r[0]}", f"SO-{r[1]}", "FULFILLS")

        # 8. Billing Documents
        bdh = conn.execute(
            text(f"SELECT * FROM {TABLE_PREFIX}billing_document_headers")
        ).mappings().fetchall()
        for r in bdh:
            bill_id = get_val(r, 'billingDocument')
            if bill_id:
                nid = f"BD-{bill_id}"
                add_node(nid, f"Billing Doc {bill_id}", "Billing Document", r)
                sold_to = get_val(r, 'soldToParty')
                if sold_to:
                    add_node(f"BP-{sold_to}", f"Customer {sold_to}", "Customer", {"customer": sold_to})
                    add_edge(f"BP-{sold_to}", nid, "BILLED_TO")

        # 9. Billing Items -> Deliveries (USE QUOTES)
        bdi = conn.execute(
            text(f"""
                SELECT "billingDocument", "referenceSdDocument"
                FROM {TABLE_PREFIX}billing_document_items
                WHERE "referenceSdDocument" IS NOT NULL AND "referenceSdDocument" != ''
                ORDER BY 1
            """)
        ).fetchall()
        for r in bdi:
            if r[0] and r[1]:
                add_edge(f"BD-{r[0]}", f"D-{r[1]}", "INVOICES")

        # 10. Journal Entries
        jei = conn.execute(
            text(f"SELECT * FROM {TABLE_PREFIX}journal_entry_items_accounts_receivable")
        ).mappings().fetchall()
        for r in jei:
            acc_doc = get_val(r, 'accountingDocument')
            if acc_doc:
                nid = f"JE-{acc_doc}"
                add_node(nid, f"Journal Entry {acc_doc}", "Journal Entry", r)
                ref_doc = get_val(r, 'referenceDocument')
                if ref_doc:
                    add_edge(nid, f"BD-{ref_doc}", "POSTS_TO")

    if focus_entity and focus_id:
        sub_nodes, sub_edges = _filter_subgraph(nodes, edges, focus_entity, focus_id)
        return {"nodes": sub_nodes, "edges": sub_edges}

    return {"nodes": nodes, "edges": edges}

def _filter_subgraph(nodes, edges, entity, eid):
    prefix = {
        "billing": "BD-", "billing_document": "BD-", "sales_order": "SO-",
        "delivery": "D-", "journal": "JE-", "journal_entry": "JE-",
        "customer": "BP-", "product": "P-"
    }
    fid = prefix.get(entity.lower().replace(" ", "_"), "") + str(eid)
    connected = {fid}
    for _ in range(5):
        for e in edges:
            if e["source"] in connected or e["target"] in connected:
                connected.add(e["source"])
                connected.add(e["target"])
    sub_n = [n for n in nodes if n["id"] in connected]
    sub_e = [e for e in edges if e["source"] in connected and e["target"] in connected]
    return sub_n or nodes[:50], sub_e or edges[:80]
