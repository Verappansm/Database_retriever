# RUN using command: streamlit run main.py
import os
import streamlit as st
import pymysql
import pandas as pd
from langchain_openai.llms import OpenAI
from apikey import openai_key  # Make sure your OpenAI API key is here

# Environment setup
os.environ['OPENAI_API_KEY'] = openai_key
llm = OpenAI(temperature=0.6)

# Database setup
db_user = "root"
db_pass = "22bce1313"  # Your database password
db_host = "localhost"
db_name = "sales_inventory"

connection = pymysql.connect(
    host=db_host,
    user=db_user,
    password=db_pass,
    database=db_name,
    cursorclass=pymysql.cursors.DictCursor
)

# Schema information function
def get_schema_info(connection):
    schema_info = {}
    with connection.cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s", (db_name,))
        tables = cursor.fetchall()
        for table in tables:
            table_name = table['TABLE_NAME']
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            schema_info[table_name] = columns
    return schema_info

schema_info = get_schema_info(connection)

# Login page and role-based access control
st.title("Employee Database Access")

def login():
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Admin", "Manager", "Employee"])
    login_button = st.button("Login")
    return username, password, role, login_button

def check_credentials(username, password, role):
    # Simulate credential check (replace with real database/authentication)
    if username == "admin" and password == "admin123" and role == "Admin":
        return "Admin"
    elif username == "manager" and password == "manager123" and role == "Manager":
        return "Manager"
    elif username == "employee" and password == "employee123" and role == "Employee":
        return "Employee"
    else:
        st.error("Invalid credentials or role!")
        return None

username, password, role, login_button = login()
if login_button:
    user_role = check_credentials(username, password, role)
    
    if user_role:
        st.success(f"Welcome, {username} ({user_role})")

        if user_role == "Admin":
            st.header("Admin Access")
            st.write("Full access to the database.")
            question = st.text_input("Ask a SQL question:")
            if question:
                prompt = f"Database schema:\n\n{schema_info}\n\nSQL query for: {question}."
                sql_query = llm(prompt).strip()
                st.write("Generated SQL Query:", sql_query)
                
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(sql_query)
                        result = cursor.fetchall()
                    df = pd.DataFrame(result)
                    st.write(df)
                except Exception as e:
                    st.error(f"Error: {e}")

        elif user_role == "Manager":
            st.header("Manager Access")
            st.write("View and query data, no modifications.")
            question = st.text_input("Ask a SQL question (read-only):")
            if question:
                prompt = f"Database schema:\n\n{schema_info}\n\nSQL query for: {question}."
                sql_query = llm(prompt).strip()
                st.write("Generated SQL Query:", sql_query)
                
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(sql_query)
                        result = cursor.fetchall()
                    df = pd.DataFrame(result)
                    st.write(df)
                except Exception as e:
                    st.error(f"Error: {e}")

        elif user_role == "Employee":
            st.header("Employee Access")
            st.write("Limited access to specific tables only.")
            table_choice = st.selectbox("Select a table to view", options=list(schema_info.keys()))
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM {table_choice} LIMIT 10")
                    result = cursor.fetchall()
                df = pd.DataFrame(result)
                st.write(df)
            except Exception as e:
                st.error(f"Error: {e}")

connection.close()
