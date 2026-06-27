# Database Retriever

A natural-language-to-SQL app built with Python and Streamlit. Type a plain-English question about your data, and the app converts it into SQL, executes it against a connected database, and displays the results in the browser.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

On first run, register a user account. Then save your API key and database connection inside the app — everything is stored locally and encrypted.

---

## Features (app.py — current version)

- Convert natural-language questions into SQL using OpenAI (GPT-4o-mini) or Google Gemini
- Execute generated queries against MySQL, PostgreSQL, or SQLite
- Review and edit the generated SQL before execution
- User registration and login with bcrypt-hashed passwords
- Encrypted per-user storage of API keys and database credentials (PBKDF2 + Fernet), stored in a local SQLite file — no environment variables needed
- Automatic schema introspection via SQLAlchemy — only the schema is sent to the LLM, never your row data
- Upload an Excel file to infer column types and load it as a database table
- Voice input for spoken queries (English, Hindi, Tamil, Telugu, Malayalam, Kannada)
- CSV download of query results
- DML/DDL guard: write operations (INSERT, UPDATE, DELETE, DROP, etc.) are blocked by default

---

## Project Structure

```
sql_proj/
├── app.py                  # Main application — run this
├── version1.py             # Prototype v1: bare-minimum NL→SQL, no auth
├── version2.py             # Prototype v2: role-based login (hardcoded credentials)
├── version3.py             # Prototype v3: real DB auth, SHA-256 password hashing
├── version4.py             # Prototype v4: full features + voice, experimental build
├── apikey.py               # API key file used by version1–3 (not used by app.py)
├── databse_creator.sql     # Sample sales_inventory MySQL schema + seed data
├── requirements.txt        # Python dependencies
└── README.md
```

---

## Version History

Each version built on the previous one. All prototype files are kept for reference.

| Version | File | Auth | LLM | Databases | Key storage |
|---------|------|------|-----|-----------|-------------|
| 1 | `version1.py` | None | LangChain + OpenAI | MySQL (hardcoded) | Plain file |
| 2 | `version2.py` | Fake (hardcoded roles) | LangChain + OpenAI | MySQL (hardcoded) | Plain file |
| 3 | `version3.py` | Real DB users, SHA-256 | LangChain + OpenAI | MySQL (hardcoded) | Plain file |
| 4 | `version4.py` | bcrypt + PBKDF2 | OpenAI + Gemini | MySQL / PostgreSQL / SQLite | Encrypted local DB |
| Current | `app.py` | bcrypt + PBKDF2 | OpenAI + Gemini | MySQL / PostgreSQL / SQLite | Encrypted local DB |

---

## Known Issues in app.py

These are documented here — the code is otherwise functional.

1. **`st.experimental_rerun()` (line 367)** — deprecated since Streamlit 1.27; causes a deprecation warning. Should be `st.rerun()`.
2. **`import secrets` (line 15)** — module is imported but never used anywhere in the file.
3. **`MetaData` import (line 25)** — imported from SQLAlchemy but never used.
4. **`df.to_sql(con=conn.connection, ...)` (line 472)** — `conn.connection` is a deprecated way to access the raw DBAPI connection in SQLAlchemy 2.0. Can fail with certain backends.
5. **Gemini model version (line 316)** — uses `gemini-1.5-flash`; newer models (`gemini-2.0-flash`, `gemini-2.5-flash`) are available.

---

## Sample Database

`databse_creator.sql` creates and seeds a `sales_inventory` MySQL database with the following schema:

```
addresses      — street, city, state, zip, country
employees      — name, phone, email
clients        — company name, address
pocs           — points of contact (name, phone, email)
branches       — links clients, addresses, employees, pocs
categories     — product categories
products       — name, price, quantity_left, quantity_sold
orders         — branch, date, discount
order_items    — order, product, quantity, price
billing        — order, billing date, total amount
```

Run it in MySQL Workbench or any MySQL client before connecting from the app.

---

## Tech Stack

| Component | Library |
|-----------|---------|
| UI | Streamlit |
| LLM (OpenAI) | `openai` SDK (GPT-4o-mini) |
| LLM (Google) | `google-generativeai` (Gemini) |
| Database layer | SQLAlchemy + PyMySQL + psycopg2-binary |
| Password hashing | bcrypt |
| Credential encryption | cryptography (Fernet, PBKDF2-HMAC-SHA256) |
| Results display | pandas |
| Voice input | streamlit-mic-recorder + SpeechRecognition |
| Excel parsing | openpyxl + pandas |

---

## Security Notes

- API keys and database credentials are stored **locally** in `app_secure.db`, encrypted with a key derived from your login password — they are never sent anywhere.
- Only the **database schema** and your **question** are sent to the LLM. Row data is never transmitted.
- `app_secure.db` and `local.db` are listed in `.gitignore` and must not be committed to a public repository.
- `apikey.py` (used by the prototype versions) is also gitignored for the same reason.
