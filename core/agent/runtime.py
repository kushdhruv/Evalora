"""core/agent/runtime.py: Real live tool execution and agent runtime."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List
from core.sdk.tracer import AgentTracer

DEMO_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "live_demo.db"


def init_demo_sqlite_db():
    """Initializes a real SQLite database file with actual business records."""
    DEMO_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DEMO_DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS invoices;")
    cur.execute("DROP TABLE IF EXISTS customers;")
    cur.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            acct_id TEXT NOT NULL,
            balance REAL NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    """)
    cur.execute("INSERT INTO customers (name, email) VALUES ('Acct 982 Corp', 'billing@acct982.corp');")
    customer_id = cur.lastrowid
    cur.execute(
        "INSERT INTO invoices (customer_id, acct_id, balance, status) VALUES (?, 'acct_982', 450.00, 'OVERDUE');",
        (customer_id,),
    )
    conn.commit()
    conn.close()


# Ensure database exists on load
init_demo_sqlite_db()


# -----------------------------------------------------------------------------
# Real Tools
# -----------------------------------------------------------------------------

def tool_run_sqlite(query: str) -> List[Dict[str, Any]]:
    """Real SQLite tool: connects to the database and executes the exact SQL query string."""
    conn = sqlite3.connect(DEMO_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute(query)
        rows = [dict(row) for row in cur.fetchall()]
        return rows
    finally:
        conn.close()


def tool_send_email(to: str, subject: str, body: str) -> Dict[str, str]:
    """Real email tool: validates recipient address and returns delivery confirmation."""
    if not to or not to.strip() or "@" not in to:
        raise ValueError("Invalid recipient address: email must be non-empty and contain '@'")
    return {
        "status": "DELIVERED",
        "to": to,
        "subject": subject,
        "body_preview": body[:40],
    }


def tool_calculate(expression: str) -> float:
    """Real math tool: evaluates mathematical expressions."""
    # Safe evaluation of basic math operations
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expression):
        raise ValueError(f"Disallowed characters in math expression: {expression}")
    return float(eval(expression, {"__builtins__": None}, {}))


# -----------------------------------------------------------------------------
# Real Agent Execution Workflows
# -----------------------------------------------------------------------------

def execute_real_agent_v1(prompt: str) -> AgentTracer:
    """Agent V1: Halucinates that table 'invoices' has column 'email_address'."""
    tracer = AgentTracer(agent_id="billing_support_agent", agent_version="1.0.0")
    tracer.record_plan(
        plan_content=f"Plan to handle prompt: '{prompt}'. Steps: [1. Query SQLite invoices, 2. Send email]",
        steps=["Query SQLite", "Send Email"],
    )

    # Step 2: Attempt flawed SQL query
    flawed_query = "SELECT balance, email_address FROM invoices WHERE acct_id = 'acct_982'"
    db_result = None
    try:
        db_result = tracer.execute_tool(
            tool_name="sqlite_query",
            tool_fn=tool_run_sqlite,
            query=flawed_query,
        )
    except Exception:
        # Agent mishandles exception: continues with None
        pass

    # Step 3: Cascading tool failure
    recipient = ""
    balance = None
    if db_result and len(db_result) > 0:
        recipient = db_result[0].get("email_address", "")
        balance = db_result[0].get("balance")

    try:
        tracer.execute_tool(
            tool_name="send_email",
            tool_fn=tool_send_email,
            to=recipient,
            subject="Overdue Balance Notice",
            body=f"Your balance is ${balance}",
        )
    except Exception:
        pass

    tracer.record_outcome(
        outcome_text="I was unable to complete your request due to an email delivery error.",
        is_success=False,
    )
    return tracer


def execute_real_agent_v2(prompt: str) -> AgentTracer:
    """Agent V2: Inspects schema, performs valid join between invoices & customers, sends real email."""
    tracer = AgentTracer(agent_id="billing_support_agent", agent_version="2.0.0")
    tracer.record_plan(
        plan_content=f"Plan to handle prompt: '{prompt}'. Steps: [1. Query invoices with customer join, 2. Send email]",
        steps=["Query invoices joined with customers", "Send Email"],
    )

    # Step 2: Valid SQL query
    valid_query = """
        SELECT i.balance, c.email 
        FROM invoices i 
        JOIN customers c ON i.customer_id = c.id 
        WHERE i.acct_id = 'acct_982'
    """
    rows = tracer.execute_tool(
        tool_name="sqlite_query",
        tool_fn=tool_run_sqlite,
        query=valid_query,
    )

    balance = rows[0]["balance"]
    email = rows[0]["email"]

    # Step 3: Valid email dispatch
    tracer.execute_tool(
        tool_name="send_email",
        tool_fn=tool_send_email,
        to=email,
        subject="Overdue Balance Notice",
        body=f"Dear Customer, your overdue balance is ${balance:.2f}.",
    )

    tracer.record_outcome(
        outcome_text=f"The overdue balance of ${balance:.2f} was verified and successfully emailed to {email}.",
        is_success=True,
    )
    return tracer
