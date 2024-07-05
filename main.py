# RUN using command streamlit run main.py
from langchain_openai.llms import OpenAI
import os   
from apikey import openai_key    #add your openai api key to the apikey file
import streamlit as st
import pymysql
import pandas as pd

os.environ['OPENAI_API_KEY'] = openai_key
llm = OpenAI(temperature=0.6)


db_user = "root"
db_pass = ""    # Enter your database password here
db_host = "localhost"
db_name = "sales_inventory"


connection = pymysql.connect(
    host=db_host,
    user=db_user,
    password=db_pass,
    database=db_name,
    cursorclass=pymysql.cursors.DictCursor  
)

# Function to retrieve schema information
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


schema_str = ""
for table, columns in schema_info.items():
    schema_str += f"Table {table}:\n"
    for column in columns:
        schema_str += f"  - {column['Field']} ({column['Type']})\n"
    schema_str += "\n"

st.title("Employee Database Q&A")

question = st.text_input("Question: ")

if question:
    # Get the SQL query from the LLM
    prompt = f"Given the following database schema:\n\n{schema_str}\nWrite an SQL query to answer the following: {question}."
    sql_query = llm(prompt).strip()
    
    st.header("Generated SQL Query: ")
    st.write(sql_query)
    
    try:
        with connection.cursor() as cursor:
            # Execute the SQL query
            cursor.execute(sql_query)
            result = cursor.fetchall()

        df = pd.DataFrame(result)
        
        st.header("Query Result: ")
        st.write(df)
    except Exception as e:
        st.error(f"Error executing query: {e}")

connection.close()