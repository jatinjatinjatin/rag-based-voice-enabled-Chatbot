import subprocess
import sqlite3
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import pandas as pd
import io

DB_PATH = Path(__file__).parent / "app.db"
MAX_LIMIT = 100

app = FastAPI(title="NLP → SQL Engine (Ollama + Secure DB)")

# =============================
# Models
# =============================

class SQLRequest(BaseModel):
    prompt: str

# =============================
# Database Helpers
# =============================

def get_db_schema() -> str:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT name, sql FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """)

    rows = cur.fetchall()
    conn.close()

    return "\n\n".join(sql + ";" for _, sql in rows)

def execute_sql(sql: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# =============================
# SQL Safety
# =============================

FORBIDDEN_KEYWORDS = {
    "delete", "drop", "update", "insert", "alter",
    "truncate", "create", "replace", "attach", "detach"
}

def enforce_sql_safety(sql: str) -> str:
    sql_clean = sql.strip().lower()

    if not sql_clean.startswith("select"):
        raise ValueError("Only SELECT queries are allowed")

    for word in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{word}\b", sql_clean):
            raise ValueError(f"Forbidden SQL operation: {word.upper()}")

    if " limit " not in sql_clean:
        sql = sql.rstrip(";") + f" LIMIT {MAX_LIMIT};"

    return sql

# =============================
# SQL Repair / Optimizer Layer
# =============================

def repair_sql(sql: str) -> str:
    sql = sql.strip()
    sql = re.sub(r"\s+", " ", sql)

    # Fix SELECT ... WHERE ... FROM table
    sql = re.sub(
        r"SELECT (.+?) WHERE (.+?) FROM ([a-zA-Z0-9_]+)",
        r"SELECT \1 FROM \3 WHERE \2",
        sql,
        flags=re.I
    )

    # Fix ORDER before FROM
    sql = re.sub(
        r"SELECT (.+?) ORDER BY (.+?) FROM ([a-zA-Z0-9_]+)",
        r"SELECT \1 FROM \3 ORDER BY \2",
        sql,
        flags=re.I
    )

    # REMOVED THE BUGGY BLOCK THAT CAUSED THE "near FROM" SYNTAX ERROR
    # The old block forcibly inserted "FROM transactions" in wrong places
    # and broke valid queries. It is no longer needed.

    # Remove duplicate FROM
    sql = re.sub(r"FROM\s+FROM", "FROM", sql, flags=re.I)

    # Ensure FROM exists
    if not re.search(r"\bfrom\b", sql, re.I):
        raise ValueError("Invalid SQL generated (missing FROM clause)")

    return sql.strip()

# =============================
# SQL Table Formatter
# =============================

def format_as_sql_table(rows):
    if not rows:
        return "(no rows)"

    headers = list(rows[0].keys())
    widths = {h: len(h) for h in headers}

    for r in rows:
        for h in headers:
            widths[h] = max(widths[h], len(str(r[h])))

    def sep():
        return "+" + "+".join("-" * (widths[h] + 2) for h in headers) + "+"

    def line(row):
        return "|" + "|".join(f" {str(row[h]).ljust(widths[h])} " for h in headers) + "|"

    out = [sep(), line({h: h for h in headers}), sep()]
    for r in rows:
        out.append(line(r))
    out.append(sep())
    return "\n".join(out)

# =============================
# Ollama SQL Generator
# =============================

def generate_sql_with_ollama(prompt: str, schema: str) -> str:
    system_prompt = f"""
You are an expert SQLite SQL generator.

Database schema:
{schema}

Rules:
- Use existing tables only
- SELECT only
- SQLite syntax
- No explanation
- Output only SQL

User request:
{prompt}
"""

    result = subprocess.run(
        ["ollama", "run", "llama3"],
        input=system_prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="ignore"))

    return result.stdout.decode("utf-8", errors="ignore").strip()

# =============================
# Routes
# =============================

@app.get("/")
def root():
    return {
        "status": "ok",
        "engine": "ollama",
        "db": "sqlite",
        "security": ["read-only", "keyword-block", "limit-injection", "sql-repair"]
    }

@app.post("/api/sql")
def query_sql(req: SQLRequest):
    try:
        schema = get_db_schema()
        raw_sql = generate_sql_with_ollama(req.prompt, schema)

        fixed_sql = repair_sql(raw_sql)
        safe_sql = enforce_sql_safety(fixed_sql)

        rows = execute_sql(safe_sql)

        return {
            "sql": safe_sql,
            "rows": rows,
            "table": format_as_sql_table(rows),
            "row_count": len(rows),
            "success": True
        }

    except Exception as e:
        print("🔥 ERROR:", e)
        raise HTTPException(status_code=400, detail=str(e))

# =============================
# CSV Upload → Auto Table
# =============================

@app.post("/api/upload_csv")
def upload_csv(file: UploadFile = File(...)):
    try:
        if not file.filename or not file.filename.endswith(".csv"):
            raise ValueError("Only CSV files allowed")

        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))

        if df.empty:
            raise ValueError("CSV is empty")

        table = file.filename.replace(".csv", "").lower().replace(" ", "_")

        conn = sqlite3.connect(DB_PATH)
        df.to_sql(table, conn, if_exists="replace", index=False)
        conn.close()

        return {
            "success": True,
            "table": table,
            "rows_inserted": len(df),
            "columns": list(df.columns)
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))