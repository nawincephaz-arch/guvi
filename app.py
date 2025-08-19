import streamlit as st
import requests
import sqlite3
import pandas as pd

# ----------------------------
# App Layout
# ----------------------------
st.set_page_config(page_title="Harvard Artifacts Explorer", layout="wide")
st.title("🏺 Harvard Artifacts Explorer")
st.write("Explore, collect, and analyze artifacts from the Harvard Art Museums API.")

# ----------------------------
# DB Setup
# ----------------------------
DB_FILE = "artifacts.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

# ----------------------------
# Fetch Data from API
# ----------------------------
API_KEY = "a1173ce4-98ad-4123-b7b2-137a0053f7c9"   # 🔑 Replace with your Harvard API key
BASE_URL = "https://api.harvardartmuseums.org/object"

def fetch_data(classification, rows=2500):
    records = []
    page = 1
    collected = 0

    st.info(f"Fetching {rows} records for {classification}...")

    while collected < rows:
        params = {
            "apikey": API_KEY,
            "classification": classification,
            "size": 100,
            "page": page
        }
        response = requests.get(BASE_URL, params=params)
        if response.status_code != 200:
            st.error(f"❌ API request failed: {response.status_code}")
            break

        data = response.json()
        if "records" not in data:
            break

        records.extend(data["records"])
        collected = len(records)
        page += 1

        if len(data["records"]) == 0:
            break

    return records[:rows]

# ----------------------------
# SQL Table Creation
# ----------------------------
def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS artifact_metadata (
        id INTEGER PRIMARY KEY,
        title TEXT,
        culture TEXT,
        period TEXT,
        century TEXT,
        medium TEXT,
        dimensions TEXT,
        description TEXT,
        department TEXT,
        classification TEXT,
        accessionyear INTEGER,
        accessionmethod TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS artifact_media (
        objectid INTEGER,
        imagecount INTEGER,
        mediacount INTEGER,
        colorcount INTEGER,
        rank INTEGER,
        datebegin INTEGER,
        dateend INTEGER,
        FOREIGN KEY (objectid) REFERENCES artifact_metadata(id)
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS artifact_colors (
        objectid INTEGER,
        color TEXT,
        spectrum TEXT,
        hue TEXT,
        percent REAL,
        css3 TEXT,
        FOREIGN KEY (objectid) REFERENCES artifact_metadata(id)
    )""")

    conn.commit()
    conn.close()

# ----------------------------
# Insert Data into Tables
# ----------------------------
def insert_into_db(records):
    conn = get_connection()
    cur = conn.cursor()

    for rec in records:
        # Insert metadata
        cur.execute("""INSERT OR REPLACE INTO artifact_metadata 
            (id, title, culture, period, century, medium, dimensions, description, department, classification, accessionyear, accessionmethod)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            rec.get("id"),
            rec.get("title"),
            rec.get("culture"),
            rec.get("period"),
            rec.get("century"),
            rec.get("medium"),
            rec.get("dimensions"),
            rec.get("description"),
            rec.get("department"),
            rec.get("classification"),
            rec.get("accessionyear"),
            rec.get("accessionmethod")
        ))

        # Insert media
        cur.execute("""INSERT INTO artifact_media 
            (objectid, imagecount, mediacount, colorcount, rank, datebegin, dateend)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", (
            rec.get("id"),
            rec.get("imagecount"),
            rec.get("mediacount"),
            rec.get("colorcount"),
            rec.get("rank"),
            rec.get("datebegin"),
            rec.get("dateend")
        ))

        # Insert colors
        if "colors" in rec and rec["colors"]:
            for c in rec["colors"]:
                cur.execute("""INSERT INTO artifact_colors 
                    (objectid, color, spectrum, hue, percent, css3)
                    VALUES (?, ?, ?, ?, ?, ?)""", (
                    rec.get("id"),
                    c.get("color"),
                    c.get("spectrum"),
                    c.get("hue"),
                    c.get("percent"),
                    c.get("css3")
                ))

    conn.commit()
    conn.close()
    st.success(f"✅ Inserted {len(records)} records into database")

# ----------------------------
# Run Queries
# ----------------------------
def run_query(query):
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# ----------------------------
# Streamlit Interface
# ----------------------------
st.subheader("⚙️ Data Collection")

classification = st.selectbox("Select a classification:", 
    ["Paintings", "Sculpture", "Coins", "Drawings", "Prints", "Jewellery"])

if st.button("Collect Data"):
    records = fetch_data(classification, 2500)
    st.session_state["records"] = records
    st.success(f"✅ Collected {len(records)} {classification}")

if "records" in st.session_state:
    if st.button("Show Data"):
        df = pd.DataFrame(st.session_state["records"])
        st.dataframe(df.head(20))

    if st.button("Insert into SQL"):
        create_tables()
        insert_into_db(st.session_state["records"])

# ----------------------------
# Query & Visualization
# ----------------------------
st.subheader("📊 Query & Visualization")

queries = {
    "Artifacts from 11th century Byzantine culture":
        "SELECT id, title, culture, century FROM artifact_metadata WHERE century = '11th century' AND culture = 'Byzantine';",
    "Unique cultures":
        "SELECT DISTINCT culture FROM artifact_metadata WHERE culture IS NOT NULL;",
    "Count of artifacts per department":
        "SELECT department, COUNT(*) as total FROM artifact_metadata GROUP BY department;",
    "Top 5 most used colors":
        "SELECT color, COUNT(*) as freq FROM artifact_colors GROUP BY color ORDER BY freq DESC LIMIT 5;"
}

choice = st.selectbox("Choose a pre-written query:", list(queries.keys()))

if st.button("Run Query"):
    sql = queries[choice]
    df = run_query(sql)
    st.write(f"### Results: {choice}")
    st.dataframe(df)

    # Example chart
    if "COUNT" in sql or "freq" in sql:
        st.bar_chart(df.set_index(df.columns[0]))
