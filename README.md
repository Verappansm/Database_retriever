# Database_retriever

A natural-language-to-SQL query generator built with LangChain and Streamlit. Type a plain-English question about your data, and the app converts it into a SQL query, executes it against a connected database, and displays the results directly in the browser.

## Description

This project lets a user ask everyday questions about a database (for example, "which client placed the most orders last month?") and have those questions automatically translated into SQL, executed, and shown as results in a Streamlit web interface. The repository contains an iterative build-out of the idea, from a simple single-database prototype through to a full multi-user application with encrypted credential storage and support for multiple LLM providers and database engines.

`app.py` is the current, fully-featured entry point. It builds on the earlier prototypes (`main.py`, `main2.py`, `main3.py`, `main4.py`, kept in the repo to show the project's evolution) by adding user accounts, encrypted storage of API keys and database credentials, support for multiple database backends, and voice input for queries.

## Features

- Convert natural-language questions into SQL using an LLM (OpenAI or Google Gemini)
- Execute generated queries against a connected database and display results in Streamlit (via pandas)
- User registration/login with bcrypt-hashed passwords
- Encrypted, per-user storage of API keys and database credentials (PBKDF2-derived key + Fernet encryption), stored locally in a SQLite database
- Support for multiple target databases: MySQL, PostgreSQL, and SQLite, with automatic schema introspection via SQLAlchemy
- Voice input for spoken questions (speech-to-text)
- Includes a sample schema and seed data (`databse_creator.sql`) for a small sales/inventory database to query against

## Tech Stack

- Python
- Streamlit (UI)
- LangChain (`langchain_openai`) in earlier prototype versions; direct OpenAI and Google Generative AI (Gemini) SDKs in the current `app.py`
- SQLAlchemy (database connection/inspection)
- PyMySQL / psycopg2-binary (MySQL/PostgreSQL drivers)
- SQLite (local encrypted credential store and optional query target)
- bcrypt (password hashing)
- cryptography / Fernet (credential encryption)
- pandas (results display)
- `streamlit_mic_recorder` + SpeechRecognition (voice input)

## Project Structure

- `app.py` — main application entry point (recommended; full-featured version with auth, encryption, multi-LLM and multi-DB support)
- `main.py`, `main2.py`, `main3.py`, `main4.py` — earlier prototype iterations, kept for reference
- `databse_creator.sql` — SQL script to create and seed a sample `sales_inventory` database (run in MySQL Workbench or similar)
- `apikey.py` — local file for storing an API key used by the earlier prototype scripts
- `requirements.txt` — Python dependencies

## Setup

1. **Install dependencies**

   ```
   pip install -r requirements.txt
   ```

2. **Set up a sample database (optional)**

   Run `databse_creator.sql` in a MySQL instance to create and populate a sample `sales_inventory` database to query against. Alternatively, connect to your own MySQL, PostgreSQL, or SQLite database from within the app.

3. **Run the application**

   ```
   streamlit run app.py
   ```

4. **Configure inside the app**

   On first run, register a user account. Once logged in, provide your OpenAI or Google Gemini API key (stored encrypted, no environment variables required) and configure your database connection details. You can then start asking natural-language questions, which the app will translate into SQL and execute, displaying the results in the interface.

## Notes

- The earlier prototype scripts (`main.py` through `main4.py`) use a hardcoded local MySQL connection and a single OpenAI-backed LangChain pipeline; they are kept in the repository to show the project's progression but `app.py` is the version intended for actual use.
- Do not commit real API keys, database passwords, or the generated local credential databases (`app_secure.db`, `local.db`) to a public repository.
