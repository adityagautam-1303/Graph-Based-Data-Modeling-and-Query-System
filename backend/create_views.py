import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/o2c_graph")
engine = create_engine(DATABASE_URL)

USE_SQLITE = "sqlite" in DATABASE_URL
schema_prefix = "o2c." if not USE_SQLITE else ""
view_schema = "o2c." if not USE_SQLITE else ""

VIEWS = [
    # 1. Customers
    f"""
    CREATE OR REPLACE VIEW {view_schema}v_customers AS
    SELECT 
        "businessPartner" AS "customerId",
        "businessPartnerName" AS "customerName"
    FROM {schema_prefix}business_partners;
    """,
    
    # 2. Products
    f"""
    CREATE OR REPLACE VIEW {view_schema}v_products AS
    SELECT 
        "product" AS "productId",
        "productType",
        "baseUnit"
    FROM {schema_prefix}products;
    """,
    
    # 3. Plants
    f"""
    CREATE OR REPLACE VIEW {view_schema}v_plants AS
    SELECT 
        "plant" AS "plantId",
        "plantName"
    FROM {schema_prefix}plants;
    """,

    # 4. Sales Orders (Merged Headers & Items)
    f"""
    CREATE OR REPLACE VIEW {view_schema}v_sales_orders AS
    SELECT 
        h."salesOrder" AS "orderId",
        h."soldToParty" AS "customerId",
        h."totalNetAmount" AS "orderTotalAmount",
        h."transactionCurrency" AS "currency",
        h."creationDate" AS "orderDate",
        h."overallDeliveryStatus" AS "deliveryStatus",
        i."salesOrderItem" AS "itemId",
        i."material" AS "productId",
        i."requestedQuantity" AS "quantity",
        i."netAmount" AS "itemAmount",
        i."productionPlant" AS "plantId"
    FROM {schema_prefix}sales_order_headers h
    LEFT JOIN {schema_prefix}sales_order_items i ON h."salesOrder" = i."salesOrder";
    """,

    # 5. Deliveries (Merged Headers & Items)
    f"""
    CREATE OR REPLACE VIEW {view_schema}v_deliveries AS
    SELECT 
        h."deliveryDocument" AS "deliveryId",
        h."shippingPoint" AS "shippingPlantId",
        h."creationDate" AS "deliveryDate",
        i."deliveryDocumentItem" AS "itemId",
        i."referenceSdDocument" AS "parentOrderId",
        i."plant" AS "plantId"
    FROM {schema_prefix}outbound_delivery_headers h
    LEFT JOIN {schema_prefix}outbound_delivery_items i ON h."deliveryDocument" = i."deliveryDocument";
    """,

    # 6. Billing Documents / Invoices (Merged Headers & Items)
    f"""
    CREATE OR REPLACE VIEW {view_schema}v_billing_documents AS
    SELECT 
        h."billingDocument" AS "invoiceId",
        h."soldToParty" AS "customerId",
        h."accountingDocument" AS "journalId",
        h."totalNetAmount" AS "invoiceTotalAmount",
        h."billingDocumentDate" AS "invoiceDate",
        h."billingDocumentIsCancelled" AS "isCancelled",
        i."billingDocumentItem" AS "itemId",
        i."material" AS "productId",
        i."referenceSdDocument" AS "parentDeliveryId"
    FROM {schema_prefix}billing_document_headers h
    LEFT JOIN {schema_prefix}billing_document_items i ON h."billingDocument" = i."billingDocument";
    """,

    # 7. Journal Entries
    f"""
    CREATE OR REPLACE VIEW {view_schema}v_journal_entries AS
    SELECT 
        "accountingDocument" AS "journalId",
        "referenceDocument" AS "parentInvoiceId",
        "glAccount",
        "amountInTransactionCurrency" AS "amount",
        "transactionCurrency" AS "currency",
        "postingDate",
        "customer" AS "customerId"
    FROM {schema_prefix}journal_entry_items_accounts_receivable;
    """,

    # 8. Payments
    f"""
    CREATE OR REPLACE VIEW {view_schema}v_payments AS
    SELECT 
        "accountingDocument" AS "paymentId",
        "clearingAccountingDocument" AS "parentJournalId",
        "amountInTransactionCurrency" AS "amount",
        "customer" AS "customerId"
    FROM {schema_prefix}payments_accounts_receivable;
    """
]

def create_views():
    with engine.begin() as conn:
        for view_sql in VIEWS:
            print(f"Executing: {view_sql.strip().splitlines()[0]}")
            conn.execute(text(view_sql))
    print("Successfully created 8 abstract SQL Views over the SAP database!")

if __name__ == "__main__":
    create_views()
