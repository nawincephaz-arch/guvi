import os, time, requests, sqlite3, pandas as pd, streamlit as st

# ------------------------
# Config & Theme
# ------------------------
st.set_page_config(page_title="Harvard Artifacts Explorer",
                   page_icon="🏺",
                   layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .stButton>button {
        border-radius: 10px;
        background-color: #4CAF50;
        color: white;
        padding: 0.5em 1em;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #45a049;
        color: white;
    }
    .stAlert {
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------
# API Setup
# ------------------------
BASE_URL = "https://api.harvardartmuseums.org/object"

def get_api_key():
    key = st.secrets.get("HARVARD_API_KEY", None)
    if not key:
        key = os.getenv("HARVARD_API_KEY")
    if not key:
        with st.sidebar:
            key = st.text_input("🔑 Enter Harvard API Key", type="password")
    return key

def test_api_key(api_key: str) -> bool:
    try:
        r = requests.get(BASE_URL, params={"apikey": api_key, "size": 1}, timeout=10)
        return r.status_code == 200
    except:
        return False

# ------------------------
# DB Setup
# ------------------------
DB_FILE = "artifacts.db"
def get_connection():
    return sqlite3.connect(DB_FILE)

def create_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS artifact_metadata (
        id INTEGER PRIMARY KEY,
        title TEXT, culture TEXT, period TEXT, century TEXT,
        medium TEXT, dimensions TEXT, description TEXT,
        department TEXT, classification TEXT,
        accessionyear INTEGER, accessionmethod TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS artifact_media (
        objectid INTEGER,
        imagecount INTEGER, mediacount INTEGER, colorcount INTEGER,
        rank INTEGER, datebegin INTEGER, dateend INTEGER,
        FOREIGN KEY (objectid) REFERENCES artifact_metadata(id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS artifact_colors (
        objectid INTEGER,
        color TEXT, spectrum TEXT, hue TEXT,
        percent REAL, css3 TEXT,
        FOREIGN KEY (objectid) REFERENCES artifact_metadata(id)
    )""")
    conn.commit()
    conn.close()

# ------------------------
# Data Fetching
# ------------------------
def fetch_data(classification, rows, api_key):
    records, page = [], 1
    bar = st.progress(0)
    while len(records) < rows:
        params = {"apikey": api_key, "classification": classification, "size": 100, "page": page}
        r = requests.get(BASE_URL, params=params, timeout=20)
        if r.status_code == 429:
            time.sleep(1)
            continue
        if r.status_code != 200:
            st.error(f"❌ API request failed: {r.status_code}")
            break
        data = r.json()
        chunk = data.get("records", [])
        if not chunk:
            break
        records.extend(chunk)
        page += 1
        bar.progress(min(len(records)/rows,1.0))
        time.sleep(0.2)
    bar.empty()
    return records[:rows]

def insert_into_db(records):
    conn = get_connection()
    cur = conn.cursor()
    for rec in records:
        # Metadata
        cur.execute("""INSERT OR REPLACE INTO artifact_metadata
            (id, title, culture, period, century, medium, dimensions,
             description, department, classification,
             accessionyear, accessionmethod)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
             (rec.get("id"), rec.get("title"), rec.get("culture"),
              rec.get("period"), rec.get("century"), rec.get("medium"),
              rec.get("dimensions"), rec.get("description"),
              rec.get("department"), rec.get("classification"),
              rec.get("accessionyear"), rec.get("accessionmethod")))
        # Media
        cur.execute("""INSERT INTO artifact_media
            (objectid, imagecount, mediacount, colorcount, rank, datebegin, dateend)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (rec.get("id"), rec.get("imagecount"), rec.get("mediacount"),
             rec.get("colorcount"), rec.get("rank"),
             rec.get("datebegin"), rec.get("dateend")))
        # Colors
        if "colors" in rec and rec["colors"]:
            for c in rec["colors"]:
                cur.execute("""INSERT INTO artifact_colors
                    (objectid, color, spectrum, hue, percent, css3)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (rec.get("id"), c.get("color"), c.get("spectrum"),
                     c.get("hue"), c.get("percent"), c.get("css3")))
    conn.commit()
    conn.close()

def run_query(query):
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# ------------------------
# Sidebar Navigation
# ------------------------
st.sidebar.title("📌 Navigation")
page = st.sidebar.radio("Go to:", ["Home", "Data Collection", "SQL Explorer", "Visualizations"])

api_key = get_api_key()
if not api_key:
    st.sidebar.warning("🔑 Add API key to start.")
    st.stop()
elif not test_api_key(api_key):
    st.sidebar.error("❌ Invalid API Key")
    st.stop()

# ------------------------
# Pages
# ------------------------
if page == "Home":
    st.header("🏺 Welcome to the Harvard Artifacts Explorer")
    st.markdown("""
    This app lets you:
    - Collect artifacts from the Harvard Art Museum API  
    - Store them into SQLite (3 linked tables)  
    - Run SQL queries interactively  
    - Visualize data in charts  
    """)

elif page == "Data Collection":
    st.header("📥 Collect & Store Data")
    classification = st.selectbox("Select Classification", ["Paintings", "Sculpture", "Coins", "Drawings", "Prints", "Jewellery"])
    rows = st.slider("Number of records", 100, 2500, 500, 100)
    if st.button("Collect Data"):
        records = fetch_data(classification, rows, api_key)
        st.session_state["records"] = records
        st.success(f"✅ Collected {len(records)} records for {classification}")
    if "records" in st.session_state:
        st.write("### Preview:")
        st.dataframe(pd.DataFrame(st.session_state["records"]).head(10))
        if st.button("Insert into Database"):
            create_tables()
            insert_into_db(st.session_state["records"])
            st.success("💾 Data inserted into SQLite")

elif page == "SQL Explorer":
    st.header("🔍 SQL Queries")
    queries = {
        "Artifacts from 11th century Byzantine culture":
            "SELECT id, title, culture, century FROM artifact_metadata WHERE century = '11th century' AND culture = 'Byzantine';",
        "Unique cultures":
            "SELECT DISTINCT culture FROM artifact_metadata WHERE culture IS NOT NULL;",
        "Artifacts per department":
            "SELECT department, COUNT(*) as total FROM artifact_metadata GROUP BY department;",
        "Top 5 most used colors":
            "SELECT color, COUNT(*) as freq FROM artifact_colors GROUP BY color ORDER BY freq DESC LIMIT 5;"
    }
    choice = st.selectbox("Choose query", list(queries.keys()))
    if st.button("Run Query"):
        df = run_query(queries[choice])
        st.dataframe(df)
        if "COUNT" in queries[choice] or "freq" in queries[choice]:
            st.bar_chart(df.set_index(df.columns[0]))

elif page == "Visualizations":
    st.header("📊 Quick Visuals")
    st.write("Visual insights from database")
    q1 = "SELECT department, COUNT(*) as total FROM artifact_metadata GROUP BY department ORDER BY total DESC LIMIT 10;"
    df1 = run_query(q1)
    st.subheader("Top Departments by Artifact Count")
    st.bar_chart(df1.set_index("department"))

    q2 = "SELECT hue, AVG(percent) as avg_cov FROM artifact_colors GROUP BY hue ORDER BY avg_cov DESC LIMIT 10;"
    df2 = run_query(q2)
    st.subheader("Average Color Coverage by Hue")
    st.bar_chart(df2.set_index("hue"))
