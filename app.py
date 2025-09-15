def initialize_db(db_path: str = "students.db") -> None:
    import sqlite3

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students(
    name    TEXT NOT NULL,
    age   INTEGER NOT NULL,
    gender TEXT NOT NULL,
    department TEXT NOT NULL,
    score   INTEGER NOT NULL
    );
    """)

    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS uq_students_row
    ON students(name, age, gender, department, score);
    """)

    rows = [
    ('richard',33,'male','data science',79),
    ('angela',28, 'female','geology',89),
    ('Olaolu',29,'female', 'web development',69),
    ('Reuben',50, 'male', 'Actural Science',86),
    ('Ayodele',21, 'female', 'Environmental Science',88),
    ('Adedoyin',42, 'male','web development',90),
    ('Fidelia',30,'female','data science',59),
    ('christopher',34, 'male', 'data science',80),
    ]
    # cur.executemany(
    # "INSERT OR IGNORE INTO students VALUES(lower(?), ?, lower(?), lower(?), ?)",
    # rows
    # )
    cur.executemany(
    "INSERT OR IGNORE INTO students(name, age, gender, department, score) "
    "VALUES(lower(?), ?, lower(?), lower(?), ?)",
    rows
    )

    conn.commit()
    conn.close()

import streamlit as st

@st.cache_resource
def ensure_db() -> str:
    db_path = "students.db"
    initialize_db(db_path)
    return db_path

DB_PATH = ensure_db()

# # Use DB_PATH in your query function
# def read_sql_query(sql: str, db_path: str = DB_PATH):

#     import sqlite3, os
#     if not os.path.exists(db_path):
#         raise FileNotFoundError(f"Database not found: {db_path}")
#         conn = sqlite3.connect(db_path)
#         conn.row_factory = sqlite3.Row

#     try:
#         cur = conn.cursor()
#         cur.execute(sql)
#         rows = cur.fetchall()
#         return [dict(r) for r in rows]

#     finally:
#         conn.close()


from dotenv import load_dotenv
import os
import re
import sqlite3
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()  # Make sure OPENAI_API_KEY is set in your .env


def get_sql(question: str) -> str:
    system_prompt = (
    "You convert English questions into a single SQLite SELECT statement for a table named " 
    "students with columns: name (TEXT), age (INTEGER), gender (TEXT), department (TEXT), score (INTEGER)."
    " Only output the SQL. No explanations. No code fences. Exactly one statement."
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    resp = llm.invoke([
    SystemMessage(content=system_prompt),
    HumanMessage(content=question),
    ])
    sql = resp.content.strip()

    # Strip accidental code fences/backticks
    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql, flags=re.IGNORECASE | re.MULTILINE).strip()

    # Keep only the first statement and re-append a semicolon
    sql = sql.split(";")[0].strip() + ";"

    # Allow only SELECT queries
    if not re.match(r"^\s*select\b", sql, re.IGNORECASE):
        raise ValueError(f"Refusing to run non-SELECT statement: {sql}")

    # Basic keyword guard
    forbidden = r"\b(drop|delete|update|insert|alter|pragma|attach|detach|vacuum)\b"
    if re.search(forbidden, sql, re.IGNORECASE):
        raise ValueError("Query contains forbidden keywords.")
    return sql


def read_sql_query(sql: str, db_path: str):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()



st.set_page_config(page_title="I can retrieve any SQL query")
st.header("Querying a Database in English; not SQL")

question = st.text_input("Ask a question about the students table:")

if st.button("Ask"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        try:
            with st.spinner("Generating SQL..."):
                sql = get_sql(question)
                st.code(sql, language="sql")

            with st.spinner("Running query..."):
                data = read_sql_query(sql, "students.db")

                if data:
                    st.dataframe(data)
                else:
                    st.info("No rows returned.")
        except Exception as e:
            st.error(str(e))


st.markdown(
    "<div style='margin-top:2em; font-size:.9em;color:#888'>"
    "Powered by RyBell Cognitive Concepts"
    "</div>",
    unsafe_allow_html=True
)