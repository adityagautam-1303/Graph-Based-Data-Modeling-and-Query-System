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
        from sqlalchemy import create_engine
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
    Returns {nodes: [...], edges: [...]} for frontend consumption.
    """
    engine = get_engine()
    nodes = []
    edges = []
    node_ids = set()

    def add_node(node_id: str, label: str, entity_type: str, data: dict):
        if node_id in node_ids:
            return
        node_ids.add(node_id)
        nodes.append({
            "id": node_id,
            "label": label,
            "entity": entity_type,
            "data": {k: str(v) if v is not None else "" for k, v in (data or {}).items()},
        })

    def add_edge(src: str, tgt: str, rel: str):
        if src in node_ids and tgt in node_ids:
            edges.append({"source": src, "target": tgt, "relation": rel})

    with engine.connect() as conn:
        # Customers
        bp = conn.execute(
            text(f"""
                SELECT *
                FROM {TABLE_PREFIX}business_partners
                WHERE "customer" IS NOT NULL AND "customer" != ''
                LIMIT :lim
            """),
            {"lim": limit},
        ).mappings().fetchall()

        for r in bp:
            nid = f"BP-{r['customer']}"
            r_dict = {k: str(v) if v is not None else "" for k, v in r.items()}
            label = r.get('businessPartnerName') or r['customer']
            add_node(nid, f"Customer {label}", "Customer", r_dict)

        # Products
        prod = conn.execute(
            text(f"""
                SELECT *
                FROM {TABLE_PREFIX}products
                LIMIT :lim
            """),
            {"lim": limit},
        ).mappings().fetchall()

        for r in prod:
            nid = f"P-{r['product']}"
            r_dict = {k: str(v) if v is not None else "" for k, v in r.items()}
            add_node(nid, f"Product {r['product']}", "Product", r_dict)

        # Plants
        plant_rows = conn.execute(
            text(f"""
                SELECT *
                FROM {TABLE_PREFIX}plants
                LIMIT :lim
            """),
            {"lim": limit},
        ).mappings().fetchall()

        for r in plant_rows:
            nid = f"PL-{r['plant']}"
            r_dict = {k: str(v) if v is not None else "" for k, v in r.items()}
            label = r.get('plantName') or r['plant']
            add_node(nid, f"Plant {label}", "Plant", r_dict)

        # Sales Orders
        so = conn.execute(
            text(f"""
                SELECT *
                FROM {TABLE_PREFIX}sales_order_headers
                LIMIT :lim
            """),
            {"lim": limit},
        ).mappings().fetchall()

        for r in so:
            nid = f"SO-{r['salesOrder']}"
            r_dict = {k: str(v) if v is not None else "" for k, v in r.items()}
            add_node(
                nid,
                f"Sales Order {r['salesOrder']}",
                "Sales Order",
                r_dict,
            )
            if r.get('soldToParty'):
                # Add edge to the existing Customer node
                add_edge(f"BP-{r['soldToParty']}", nid, "PLACES_ORDER")

        # Sales Order Items -> Material
        soi = conn.execute(
            text(f"""
                SELECT DISTINCT soh."salesOrder", soi.material
                FROM {TABLE_PREFIX}sales_order_items soi
                JOIN {TABLE_PREFIX}sales_order_headers soh ON soh."salesOrder" = soi."salesOrder"
                LIMIT :lim
            """),
            {"lim": limit},
        ).fetchall()

        for r in soi:
            if r[1]:
                # If product doesn't exist yet, this will create an empty shell. If it exists, add_node safely ignores it!
                add_node(f"P-{r[1]}", f"Product {r[1]}", "Product", {"product": r[1]})
                add_edge(f"SO-{r[0]}", f"P-{r[1]}", "CONTAINS_ITEM")

        # Deliveries
        odh = conn.execute(
            text(f"""
                SELECT *
                FROM {TABLE_PREFIX}outbound_delivery_headers
                LIMIT :lim
            """),
            {"lim": limit},
        ).mappings().fetchall()

        for r in odh:
            nid = f"D-{r['deliveryDocument']}"
            r_dict = {k: str(v) if v is not None else "" for k, v in r.items()}
            add_node(nid, f"Delivery {r['deliveryDocument']}", "Delivery", r_dict)
            if r.get('shippingPoint'):
                add_node(f"PL-{r['shippingPoint']}", f"Plant {r['shippingPoint']}", "Plant", {"plant": r['shippingPoint']})
                add_edge(nid, f"PL-{r['shippingPoint']}", "SHIPPED_FROM")

        # Delivery -> Sales Order
        odi = conn.execute(
            text(f"""
                SELECT DISTINCT "deliveryDocument", "referenceSdDocument"
                FROM {TABLE_PREFIX}outbound_delivery_items
                WHERE "referenceSdDocument" IS NOT NULL AND "referenceSdDocument" != ''
                LIMIT :lim
            """),
            {"lim": limit},
        ).fetchall()

        for r in odi:
            add_edge(f"D-{r[0]}", f"SO-{r[1]}", "FULFILLS")

        # Billing Documents
        bdh = conn.execute(
            text(f"""
                SELECT *
                FROM {TABLE_PREFIX}billing_document_headers
                WHERE ("billingDocumentIsCancelled" IS NULL OR lower(cast("billingDocumentIsCancelled" as text)) IN ('0', 'false'))
                LIMIT :lim
            """),
            {"lim": limit},
        ).mappings().fetchall()

        for r in bdh:
            nid = f"BD-{r['billingDocument']}"
            r_dict = {k: str(v) if v is not None else "" for k, v in r.items()}
            add_node(
                nid,
                f"Billing Doc {r['billingDocument']}",
                "Billing Document",
                r_dict,
            )
            if r.get('soldToParty'):
                add_node(f"BP-{r['soldToParty']}", f"Customer {r['soldToParty']}", "Customer", {"customer": r['soldToParty']})
                add_edge(f"BP-{r['soldToParty']}", nid, "BILLED_TO")

        # Billing Item -> Delivery
        bdi = conn.execute(
            text(f"""
                SELECT "billingDocument", "referenceSdDocument"
                FROM {TABLE_PREFIX}billing_document_items
                WHERE "referenceSdDocument" IS NOT NULL AND "referenceSdDocument" != ''
                LIMIT :lim
            """),
            {"lim": limit},
        ).fetchall()

        for r in bdi:
            add_edge(f"BD-{r[0]}", f"D-{r[1]}", "INVOICES")

        # Journal Entry
        jei = conn.execute(
            text(f"""
                SELECT *
                FROM {TABLE_PREFIX}journal_entry_items_accounts_receivable
                WHERE "referenceDocument" IS NOT NULL AND "referenceDocument" != ''
                LIMIT :lim
            """),
            {"lim": limit},
        ).mappings().fetchall()

        for r in jei:
            tgt_bd = f"BD-{r['referenceDocument']}"
            if tgt_bd in node_ids:
                nid = f"JE-{r['accountingDocument']}"
                r_dict = {k: str(v) if v is not None else "" for k, v in r.items()}
                add_node(
                    nid,
                    f"Journal Entry {r['accountingDocument']}",
                    "Journal Entry",
                    r_dict,
                )
                add_edge(nid, tgt_bd, "POSTS_TO")

    # If focus provided, filter/emphasize subgraph
    if focus_entity and focus_id:
        sub_nodes, sub_edges = _filter_subgraph(nodes, edges, focus_entity, focus_id)
        return {"nodes": sub_nodes, "edges": sub_edges}

    return {"nodes": nodes, "edges": edges}


def _filter_subgraph(
    nodes: list, edges: list, entity: str, eid: str
) -> tuple[list, list]:
    """Extract subgraph around a focus entity."""
    prefix = {"billing": "BD-", "sales_order": "SO-", "delivery": "D-", "journal": "JE-", "customer": "BP-", "product": "P-"}
    fid = prefix.get(entity.lower().replace(" ", "_"), "") + str(eid)
    if fid not in {n["id"] for n in nodes}:
        for n in nodes:
            if eid in n.get("id", "") or str(eid) in str(n.get("data", {}).values()):
                fid = n["id"]
                break

    connected = {fid}
    for _ in range(5):
        for e in edges:
            if e["source"] in connected or e["target"] in connected:
                connected.add(e["source"])
                connected.add(e["target"])

    sub_n = [n for n in nodes if n["id"] in connected]
    sub_e = [e for e in edges if e["source"] in connected and e["target"] in connected]
    return sub_n or nodes[:50], sub_e or edges[:80]
