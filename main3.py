import os
import streamlit as st
import pymysql
import pandas as pd
from langchain_openai.llms import OpenAI
from apikey import openai_key  # Ensure your OpenAI API key is here
import hashlib

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

# Hashing function for password security
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to check if user exists
def user_exists(username):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone() is not None

# Function to add a new user to the database
def add_user(username, password, role):
    hashed_password = hash_password(password)
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, hashed_password, role))
        connection.commit()

# Function to authenticate user credentials
def authenticate_user(username, password):


































































    hashed_password = hash_password(password)
    with connection.cursor() as cursor:
        cursor.execute("SELECT role FROM users WHERE username = %s AND password = %s", (username, hashed_password))
        user = cursor.fetchone()






















        if user:
            return user['role']
    return None

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

# Check if user is logged in using session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

# Main app
st.title("Employee Database Access System")

# UI for Login and Signup
if not st.session_state.logged_in:
    auth_option = st.sidebar.selectbox("Choose an option", ["Login", "Sign Up"])

    if auth_option == "Sign Up":
        st.header("Sign Up")
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        role = st.selectbox("Role", ["Admin", "Manager", "Employee"])

        if st.button("Register"):
            if new_password != confirm_password:
                st.error("Passwords do not match!")
            elif user_exists(new_username):
                st.error("Username already exists!")
            else:
                add_user(new_username, new_password, role)
                st.success("Account created successfully! Please login to continue.")

    elif auth_option == "Login":
        st.header("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user_role = authenticate_user(username, password)
            
            if user_role:
                st.session_state.logged_in = True
                st.session_state.user_role = user_role
                st.session_state.username = username
                st.success(f"Welcome, {username} ({user_role})")
            else:
                st.error("Invalid username or password!")

# After login, show the appropriate dashboard
if st.session_state.logged_in:
    schema_info = get_schema_info(connection)

    if st.session_state.user_role == "Admin":
        st.header("Admin Dashboard")
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

    elif st.session_state.user_role == "Manager":
        st.header("Manager Dashboard")
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

    elif st.session_state.user_role == "Employee":
        st.header("Employee Dashboard")
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

# Close the database connection when app ends
connection.close()
