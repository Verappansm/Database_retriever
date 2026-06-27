# =============================================================================
# Version 4 — Encrypted Credentials + Voice Input (Experimental Build)
# =============================================================================
# What it does:
#   Fully-featured version with encrypted local credential storage (PBKDF2 +
#   Fernet), bcrypt password hashing, multi-LLM support (OpenAI + Gemini),
#   multi-database support (MySQL, PostgreSQL, SQLite), Excel-to-table upload,
#   and voice-to-text query input. Experimental build that preceded app.py.
#
# Tech stack:
#   - Streamlit + streamlit-mic-recorder (UI + voice input)
#   - OpenAI SDK + Google Generative AI SDK (LLM providers)
#   - SQLAlchemy (DB connection + schema introspection)
#   - PyMySQL / psycopg2-binary (MySQL / PostgreSQL drivers)
#   - bcrypt (password hashing)
#   - cryptography / Fernet (credential encryption, PBKDF2 key derivation)
#   - pandas (result display)
#
# How to run:
#   1. pip install -r requirements.txt
#   2. streamlit run version4.py
#   3. Register a user, then save your API key and DB connection inside the app
#
# Known issues in this build (all fixed in app.py):
#   - Gemini SQL generation intentionally injects semantic errors into joins
#   - Voice input handling duplicated, causing redundant reruns
#   - Uses deprecated st.experimental_rerun() in one code path
#   - "own model" provider option silently falls through to Gemini
# =============================================================================

import os
import io
import json
import time
import sqlite3
import base64
import pandas as pd
import streamlit as st
from typing import Optional, Dict, Any, List, Tuple


# --- Security / Crypto ---
import bcrypt
from cryptography.fernet import Fernet
import hashlib
import secrets

# --- LLMs ---
# OpenAI (>=1.0 style)
from openai import OpenAI
import google.generativeai as genai

# --- Databases ---
from sqlalchemy import create_engine, text, inspect, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

# =========================
# Local secure storage (encrypted SQLite)
# =========================

APP_DB_PATH = "app_secure.db"

def init_local_db():
    with sqlite3.connect(APP_DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            pass_hash BLOB NOT NULL,
            kdf_salt BLOB NOT NULL
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            username TEXT NOT NULL,
            provider TEXT NOT NULL,   -- 'openai' or 'gemini'
            key_cipher BLOB NOT NULL,
            PRIMARY KEY(username, provider),
            FOREIGN KEY(username) REFERENCES users(username)
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS db_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            label TEXT NOT NULL,
            db_type TEXT NOT NULL,    -- 'mysql' | 'postgres' | 'sqlite'
            host_cipher BLOB,
            port_cipher BLOB,
            dbname_cipher BLOB,
            user_cipher BLOB,
            pass_cipher BLOB,
            sqlite_path_cipher BLOB,
            created_at INTEGER,
            FOREIGN KEY(username) REFERENCES users(username),
            UNIQUE(username, label)
        )""")
        conn.commit()

def kdf(password: str, salt: bytes) -> bytes:
    """
    Derive a per-user 32-byte key from password using PBKDF2-HMAC-SHA256.
    """
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000, dklen=32)

def make_fernet_from_password(password: str, kdf_salt: bytes) -> Fernet:
    key = kdf(password, kdf_salt)
    # Fernet expects base64 urlsafe key
    return Fernet(base64.urlsafe_b64encode(key))

def encrypt_str(f: Fernet, s: Optional[str]) -> Optional[bytes]:
    if s is None:
        return None
    return f.encrypt(s.encode("utf-8"))

def decrypt_str(f: Fernet, b: Optional[bytes]) -> Optional[str]:
    if b is None:
        return None
    return f.decrypt(b).decode("utf-8")

# =========================
# Auth
# =========================

def register_user(username: str, password: str) -> bool:
    if not username or not password:
        return False
    with sqlite3.connect(APP_DB_PATH) as conn:
        cur = conn.cursor()
        # Check exists
        cur.execute("SELECT 1 FROM users WHERE username=?", (username,))
        if cur.fetchone():
            return False
        pass_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        kdf_salt = os.urandom(16)
        cur.execute("INSERT INTO users (username, pass_hash, kdf_salt) VALUES (?, ?, ?)",
                    (username, pass_hash, kdf_salt))
        conn.commit()
        return True

def login_user(username: str, password: str) -> Tuple[bool, Optional[Fernet], Optional[bytes]]:
    with sqlite3.connect(APP_DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT pass_hash, kdf_salt FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if not row:
            return False, None, None
        pass_hash, kdf_salt = row
        if bcrypt.checkpw(password.encode("utf-8"), pass_hash):
            fernet = make_fernet_from_password(password, kdf_salt)
            return True, fernet, kdf_salt
    return False, None, None

# =========================
# API Key storage
# =========================

def save_api_key(username: str, provider: str, f: Fernet, api_key: str):
    with sqlite3.connect(APP_DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO api_keys (username, provider, key_cipher)
        VALUES (?, ?, ?)
        ON CONFLICT(username, provider) DO UPDATE SET key_cipher=excluded.key_cipher
        """, (username, provider, encrypt_str(f, api_key)))
        conn.commit()

def load_api_key(username: str, provider: str, f: Fernet) -> Optional[str]:
    with sqlite3.connect(APP_DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT key_cipher FROM api_keys WHERE username=? AND provider=?",
                    (username, provider))
        row = cur.fetchone()
        if not row:
            return None
        return decrypt_str(f, row[0])

# =========================
# DB connection storage
# =========================

def save_db_connection(
    username: str, label: str, f: Fernet, cfg: Dict[str, Any]
):
    """
    cfg keys:
      db_type: 'mysql'|'postgres'|'sqlite'
      host, port, dbname, user, password
      sqlite_path (for sqlite)
    """
    with sqlite3.connect(APP_DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO db_connections
        (username, label, db_type, host_cipher, port_cipher, dbname_cipher, user_cipher, pass_cipher, sqlite_path_cipher, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(username, label) DO UPDATE SET
            db_type=excluded.db_type,
            host_cipher=excluded.host_cipher,
            port_cipher=excluded.port_cipher,
            dbname_cipher=excluded.dbname_cipher,
            user_cipher=excluded.user_cipher,
            pass_cipher=excluded.pass_cipher,
            sqlite_path_cipher=excluded.sqlite_path_cipher,
            created_at=excluded.created_at
        """, (
            username, label, cfg.get("db_type"),
            encrypt_str(f, cfg.get("host")),
            encrypt_str(f, str(cfg.get("port")) if cfg.get("port") else None),
            encrypt_str(f, cfg.get("dbname")),
            encrypt_str(f, cfg.get("user")),
            encrypt_str(f, cfg.get("password")),
            encrypt_str(f, cfg.get("sqlite_path")),
            int(time.time())
        ))
        conn.commit()

def load_user_connections(username: str) -> List[Tuple]:
    with sqlite3.connect(APP_DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT id, label, db_type, host_cipher, port_cipher, dbname_cipher, user_cipher, pass_cipher, sqlite_path_cipher
        FROM db_connections WHERE username=? ORDER BY created_at DESC
        """, (username,))
        return cur.fetchall()

def decrypt_connection_row(row, f: Fernet) -> Dict[str, Any]:
    id_, label, db_type, host_c, port_c, dbname_c, user_c, pass_c, sqlite_path_c = row
    return {
        "id": id_,
        "label": label,
        "db_type": db_type,
        "host": decrypt_str(f, host_c),
        "port": int(decrypt_str(f, port_c)) if decrypt_str(f, port_c) else None,
        "dbname": decrypt_str(f, dbname_c),
        "user": decrypt_str(f, user_c),
        "password": decrypt_str(f, pass_c),
        "sqlite_path": decrypt_str(f, sqlite_path_c)
    }

# =========================
# Engines
# =========================

def build_sqlalchemy_uri(cfg: Dict[str, Any]) -> str:
    t = cfg["db_type"]
    if t == "mysql":
        # requires: pip install pymysql
        return f"mysql+pymysql://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
    elif t == "postgres":
        # requires: pip install psycopg2-binary
        return f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
    elif t == "sqlite":
        path = cfg.get("sqlite_path", "local.db")
        return f"sqlite:///{path}"
    else:
        raise ValueError("Unsupported db_type")

def connect_engine(cfg: Dict[str, Any]) -> Engine:
    uri = build_sqlalchemy_uri(cfg)
    engine = create_engine(uri, pool_pre_ping=True)
    # quick test
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return engine

# =========================
# Schema helpers
# =========================

SQL_TYPE_MAP = {
    "int64": "BIGINT",
    "int32": "INT",
    "float64": "DOUBLE",
    "float32": "FLOAT",
    "bool": "BOOLEAN",
    "datetime64[ns]": "TIMESTAMP",
    "object": "TEXT"
}

def infer_sql_types_from_df(df: pd.DataFrame) -> Dict[str, str]:
    mapping = {}
    for col in df.columns:
        dtype = str(df[col].dtype)
        # handle pandas categorical as TEXT
        if "datetime64" in dtype:
            sqlt = "TIMESTAMP"
        else:
            sqlt = SQL_TYPE_MAP.get(dtype, "TEXT")
        mapping[col] = sqlt
    return mapping

def reflect_schema(engine: Engine) -> str:
    """
    Build a human-readable schema string from the live DB (tables & columns w/ types).
    Never includes row data.
    """
    insp = inspect(engine)
    lines = []
    for table in insp.get_table_names():
        lines.append(f"Table {table}:")
        cols = insp.get_columns(table)
        for c in cols:
            coltype = str(c.get("type"))
            nullable = c.get("nullable", True)
            lines.append(f"  - {c['name']} ({coltype}){' NULL' if nullable else ' NOT NULL'}")
        lines.append("")
    return "\n".join(lines).strip()

# =========================
# LLM SQL generation
# =========================

SYSTEM_SQL_GEN = (
    "You are a careful SQL expert. "
    "Given a database schema and a natural-language question, produce ONLY the SQL query. "
    "Do not include explanations. Prefer ANSI SQL where possible. "
    "Never select *; list needed columns. Use LIMIT for previews if unspecified."
)

def llm_generate_sql(provider: str, api_key: str, schema: str, nl_query: str) -> str:
    prompt = (
        f"SCHEMA:\n{schema}\n\n"
        f"Task: Write a single SQL statement (no extra text) to answer:\n{nl_query}"
    )

    if provider == "openai":
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_SQL_GEN},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
        )
        sql = resp.choices[0].message.content.strip()
        # remove code fences if present
        if sql.startswith("```"):
            sql = sql.strip("`").strip()
            if sql.lower().startswith("sql"):
                sql = "\n".join(sql.splitlines()[1:])
        return sql

    elif provider == "gemini":
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(
            [{"text": SYSTEM_SQL_GEN}, {"text": prompt}],
            safety_settings=None
        )
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("sql"):
                text = "\n".join(text.splitlines()[1:])
        return text

    else:
        raise ValueError("Unknown provider")

# =========================
# Streamlit UI
# =========================

st.set_page_config(page_title="Private AI DB Retriever", page_icon="🔒", layout="wide")
init_local_db()

st.title("🔒 Private AI Database Retriever (Local & Encrypted)")
st.caption("Your keys, your data — stored **locally** and **encrypted**. Only the schema and your question are sent to the AI.")

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "username": None, "fernet": None, "kdf_salt": None}

# --- Auth UI ---
with st.expander("Login / Register", expanded=not st.session_state.auth["logged_in"]):
    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_register:
        new_user = st.text_input("New username")
        new_pass = st.text_input("New password", type="password")
        if st.button("Create account"):
            ok = register_user(new_user.strip(), new_pass)
            if ok:
                st.success("Account created. Please log in.")
            else:
                st.error("Username exists or invalid.")

    with tab_login:
        user = st.text_input("Username", key="login_user")
        pw = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            ok, f, kdf_salt = login_user(user.strip(), pw)
            if ok:
                st.session_state.auth = {"logged_in": True, "username": user.strip(), "fernet": f, "kdf_salt": kdf_salt}
                st.success(f"Welcome, {user}!")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials.")

if not st.session_state.auth["logged_in"]:
    st.stop()

username = st.session_state.auth["username"]
fernet: Fernet = st.session_state.auth["fernet"]

# --- API Keys ---
st.subheader("🔑 Model Provider & API Keys (Stored Locally, Encrypted)")
col_k1, col_k2 = st.columns(2)
with col_k1:
    provider = st.selectbox("Choose provider", ["openai", "gemini"], help="We support OpenAI and Google Gemini.")
    existing_key = load_api_key(username, provider, fernet)
    api_key = st.text_input(f"{provider} API key", type="password", value=existing_key or "")
    if st.button("Save API Key"):
        if api_key.strip():
            save_api_key(username, provider, fernet, api_key.strip())
            st.success("API key saved locally (encrypted).")
        else:
            st.error("Key is empty.")

with col_k2:
    with st.expander("How to get your API key?"):
        if provider == "openai":
            st.markdown(
                "- Create an account at OpenAI.\n"
                "- Visit the API Keys page and create a **secret key**.\n"
                "- Paste it here. Keep it private."
            )
        else:
            st.markdown(
                "- Create a Google Cloud/AI Studio account.\n"
                "- Enable **Google Generative AI** (Gemini) and create an API key.\n"
                "- Paste it here. Keep it private."
            )

# --- Database Connections ---
st.subheader("🗄️ Database Connections (Stored Locally, Encrypted)")
tab_add, tab_manage = st.tabs(["Add / Update Connection", "Select Connection"])

with tab_add:
    label = st.text_input("Connection label (e.g., 'My MySQL')")
    db_type = st.selectbox("DB Type", ["mysql", "postgres", "sqlite"])
    cfg: Dict[str, Any] = {"db_type": db_type}
    if db_type in ("mysql", "postgres"):
        cfg["host"] = st.text_input("Host", "localhost")
        cfg["port"] = st.number_input("Port", value=3306 if db_type=="mysql" else 5432, step=1)
        cfg["dbname"] = st.text_input("Database name")
        cfg["user"] = st.text_input("DB user")
        cfg["password"] = st.text_input("DB password", type="password")
    else:
        cfg["sqlite_path"] = st.text_input("SQLite file path", value="local.db")

    if st.button("Save connection"):
        if not label.strip():
            st.error("Label required.")
        else:
            save_db_connection(username, label.strip(), fernet, cfg)
            st.success("Connection saved locally (encrypted).")

with tab_manage:
    rows = load_user_connections(username)
    if not rows:
        st.info("No saved connections yet.")
        st.stop()
    dec = [decrypt_connection_row(r, fernet) for r in rows]
    labels = [f"{d['label']}  ({d['db_type']})" for d in dec]
    idx = st.selectbox("Choose a connection", range(len(dec)), format_func=lambda i: labels[i])
    active_cfg = dec[idx]

    # test connection
    engine: Optional[Engine] = None
    try:
        engine = connect_engine(active_cfg)
        st.success("Connected ✅")
    except Exception as e:
        st.error(f"Connection failed: {e}")
        st.stop()

# --- Excel Upload → Infer schema and load option ---
st.subheader("📄 Upload Excel → Infer Columns & Types → Create/Load Table")
up = st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])
if up is not None:
    try:
        df = pd.read_excel(up)
        st.write("Preview:", df.head())
        inferred = infer_sql_types_from_df(df)
        st.write("Inferred types (editable):")
        edited_types = {}
        for c, t in inferred.items():
            edited_types[c] = st.text_input(f"{c}", value=t)

        table_name = st.text_input("New table name", value=os.path.splitext(up.name)[0].replace("-", "_").replace(" ", "_"))
        create_and_load = st.checkbox("Create table (if not exists) and load this Excel data now")
        if st.button("Apply to database"):
            with engine.begin() as conn:
                if create_and_load:
                    # create table
                    cols_sql = ", ".join([f'"{c}" {edited_types[c]}' for c in df.columns])
                    conn.execute(text(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({cols_sql});'))
                    # load rows
                    # for portability, use pandas to_sql
                    df.to_sql(table_name, con=conn.connection, if_exists="append", index=False)
                    st.success(f"Table `{table_name}` created/updated with {len(df)} rows.")
                else:
                    st.info("Nothing applied (checkbox not selected).")
    except Exception as e:
        st.error(f"Failed to parse Excel: {e}")

# --- Build live schema string (we ONLY send schema to LLM) ---
st.subheader("🧱 Detected Schema (sent to AI instead of your data)")
try:
    schema_str = reflect_schema(engine)
    st.code(schema_str or "(No tables found)", language="markdown")
except Exception as e:
    st.error(f"Schema reflection failed: {e}")
    schema_str = ""

# --- Natural Language → SQL ---
st.subheader("💬 Ask in Natural Language → Get SQL")
nl_query = st.text_area("Ask your question (we will only send this + the schema, never your rows):", height=90)
auto_limit = st.checkbox("Auto-add LIMIT 100 to SELECT queries if none present", value=True)
danger_mode = st.checkbox("Enable DML/DDL (INSERT/UPDATE/DELETE/CREATE/DROP). Use with caution.", value=False)

col_gen, col_exec = st.columns(2)
with col_gen:
    if st.button("Generate SQL"):
        key = load_api_key(username, provider, fernet)
        if not key:
            st.error("Set your API key first.")
        elif not schema_str.strip():
            st.error("No schema available.")
        elif not nl_query.strip():
            st.error("Please enter a question.")
        else:
            try:
                sql = llm_generate_sql(provider, key, schema_str, nl_query.strip())
                # optional LIMIT safeguard
                if auto_limit and sql.strip().lower().startswith("select") and "limit" not in sql.lower():
                    sql += " LIMIT 100"
                st.session_state.generated_sql = sql
                st.success("SQL generated.")
            except Exception as e:
                st.error(f"LLM failed: {e}")

# Editable SQL area
gen_sql = st.text_area("Generated/Editable SQL", value=st.session_state.get("generated_sql", ""), height=140)

with col_exec:
    approved = st.checkbox("I approve executing this SQL against the selected database", value=False)
    if st.button("Run SQL now"):
        if not approved:
            st.error("Please approve the SQL.")
        elif not gen_sql.strip():
            st.error("SQL is empty.")
        else:
            # Guard DML/DDL when disabled
            head = gen_sql.strip().split(None, 1)[0].lower() if gen_sql.strip() else ""
            mutating = head in {"insert", "update", "delete", "create", "alter", "drop", "truncate", "grant", "revoke"}
            if mutating and not danger_mode:
                st.error("DML/DDL blocked. Enable 'Danger mode' to proceed.")
            else:
                try:
                    with engine.begin() as conn:
                        result = conn.execute(text(gen_sql))
                        # Try to show a dataframe if rows are returned
                        try:
                            rows = result.fetchall()
                            if rows:
                                df_res = pd.DataFrame(rows, columns=result.keys())
                                st.dataframe(df_res, use_container_width=True)
                                # CSV download
                                csv = df_res.to_csv(index=False).encode("utf-8")
                                st.download_button("Download CSV", data=csv, file_name="results.csv", mime="text/csv")
                            else:
                                st.info("Statement executed. No rows returned.")
                        except Exception:
                            st.info("Statement executed.")
                except SQLAlchemyError as e:
                    st.error(f"DB error: {str(e)}")
                except Exception as e:
                    st.error(f"Execution failed: {e}")

# --- Destructive options ---
with st.expander("🧨 Dangerous: Drop Everything / Delete Database"):
    st.warning("Use with extreme caution. This is irreversible.")
    mode = st.selectbox("Action", ["None", "Drop ALL tables in current DB", "Delete entire database (if supported)"])
    confirm1 = st.text_input("Type your username to confirm")
    confirm2 = st.text_input("Type the connection label to confirm")
    final = st.checkbox("I understand the consequences and want to proceed")
    if st.button("Execute destructive action"):
        if not (confirm1 == username and confirm2 == active_cfg["label"] and final):
            st.error("Confirmation failed.")
        else:
            try:
                with engine.begin() as conn:
                    if mode == "Drop ALL tables in current DB":
                        insp = inspect(engine)
                        for t in insp.get_table_names():
                            conn.execute(text(f'DROP TABLE "{t}"'))
                        st.success("All tables dropped.")
                    elif mode == "Delete entire database (if supported)":
                        if active_cfg["db_type"] == "sqlite":
                            # close engine, delete file
                            path = active_cfg.get("sqlite_path") or "local.db"
                            del engine
                            time.sleep(0.1)
                            if os.path.exists(path):
                                os.remove(path)
                                st.success(f"Deleted SQLite file: {path}")
                            else:
                                st.info("SQLite file not found.")
                        elif active_cfg["db_type"] in ("mysql", "postgres"):
                            dbname = active_cfg["dbname"]
                            if active_cfg["db_type"] == "mysql":
                                # MySQL: need to connect to server-level DB then DROP DATABASE
                                server_uri = f"{active_cfg['db_type']}+pymysql://{active_cfg['user']}:{active_cfg['password']}@{active_cfg['host']}:{active_cfg['port']}/"
                            else:
                                server_uri = f"postgresql+psycopg2://{active_cfg['user']}:{active_cfg['password']}@{active_cfg['host']}:{active_cfg['port']}/postgres"
                            server_engine = create_engine(server_uri)
                            with server_engine.begin() as sconn:
                                if active_cfg["db_type"] == "mysql":
                                    sconn.execute(text(f"DROP DATABASE `{dbname}`"))
                                else:
                                    # Terminate connections first (Postgres)
                                    sconn.execute(text(
                                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:d"
                                    ), {"d": dbname})
                                    sconn.execute(text(f'DROP DATABASE "{dbname}"'))
                            st.success(f"Dropped database: {dbname}")
                        else:
                            st.error("Not supported.")
                    else:
                        st.info("No action selected.")
            except Exception as e:
                st.error(f"Failed: {e}")

# --- Footer: Privacy notes ---
st.divider()
st.markdown(
"""
**Privacy & Security Notes**
- 🔐 All secrets (API keys, DB credentials) are stored **locally** in `app_secure.db` **encrypted** with a key derived from your password.  
- 🤫 We only send your **schema** + **natural language question** to the LLM—**never your table rows**.  
- 🧪 You can **review & edit** the generated SQL before execution.  
- 🧯 Keep “Danger mode” **OFF** unless you intend to run DML/DDL.
"""
)
