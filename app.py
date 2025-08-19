import streamlit as st
import sqlite3
import pandas as pd

# -----------------------
# DB Connection Function
# -----------------------
def run_query(query):
    conn = sqlite3.connect("artifacts.db")
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# -----------------------
# Streamlit App Layout
# -----------------------
st.set_page_config(page_title="Harvard Artifacts Explorer", layout="wide")

st.title("🏺 Harvard Artifacts Explorer")
st.write("Explore metadata, media, and colors from the Harvard Art Museums API dataset.")

# -----------------------
# Predefined Queries
# -----------------------
queries = {
    # 🏺 artifact_metadata
    "Artifacts from 11th century Byzantine culture":
        "SELECT id, title, culture, century FROM artifact_metadata WHERE century = '11th century' AND culture = 'Byzantine';",

    "Unique cultures":
        "SELECT DISTINCT culture FROM artifact_metadata WHERE culture IS NOT NULL;",

    "Artifacts from Archaic Period":
        "SELECT id, title, period FROM artifact_metadata WHERE period = 'Archaic Period';",

    "Artifact titles ordered by accession year (DESC)":
        "SELECT title, accessionyear FROM artifact_metadata ORDER BY accessionyear DESC;",

    "Count of artifacts per department":
        "SELECT department, COUNT(*) as total FROM artifact_metadata GROUP BY department;",

    # 🖼️ artifact_media
    "Artifacts with more than 1 image":
        "SELECT objectid, imagecount FROM artifact_media WHERE imagecount > 1;",

    "Average rank of artifacts":
        "SELECT AVG(rank) as avg_rank FROM artifact_media;",

    "Artifacts with higher colorcount than mediacount":
        "SELECT objectid, colorcount, mediacount FROM artifact_media WHERE colorcount > mediacount;",

    "Artifacts created between 1500 and 1600":
        "SELECT objectid, datebegin, dateend FROM artifact_media WHERE datebegin >= 1500 AND dateend <= 1600;",

    "Artifacts with no media files":
        "SELECT COUNT(*) as no_media FROM artifact_media WHERE mediacount = 0;",

    # 🎨 artifact_colors
    "Distinct hues used":
        "SELECT DISTINCT hue FROM artifact_colors;",

    "Top 5 most used colors":
        "SELECT color, COUNT(*) as freq FROM artifact_colors GROUP BY color ORDER BY freq DESC LIMIT 5;",

    "Average coverage % per hue":
        "SELECT hue, AVG(percent) as avg_coverage FROM artifact_colors GROUP BY hue;",

    "Colors for a given artifact ID (example: 12345)":
        "SELECT objectid, color, hue, percent FROM artifact_colors WHERE objectid = 12345;",

    "Total number of color entries":
        "SELECT COUNT(*) as total_colors FROM artifact_colors;",

    # 🔗 Join queries
    "Byzantine artifacts with hues":
        "SELECT m.title, c.hue FROM artifact_metadata m JOIN artifact_colors c ON m.id = c.objectid WHERE m.culture = 'Byzantine';",

    "Each artifact with its hues":
        "SELECT m.title, c.hue FROM artifact_metadata m LEFT JOIN artifact_colors c ON m.id = c.objectid;",

    "Titles, cultures, and ranks where period is not null":
        "SELECT m.title, m.culture, me.rank FROM artifact_metadata m JOIN artifact_media me ON m.id = me.objectid WHERE m.period IS NOT NULL;",

    "Top 10 ranked artifacts with hue 'Grey'":
        "SELECT m.title, me.rank, c.hue FROM artifact_metadata m JOIN artifact_media me ON m.id = me.objectid JOIN artifact_colors c ON m.id = c.objectid WHERE c.hue = 'Grey' ORDER BY me.rank ASC LIMIT 10;",

    "Artifacts per classification + avg media count":
        "SELECT m.classification, COUNT(*) as total_artifacts, AVG(me.mediacount) as avg_media FROM artifact_metadata m JOIN artifact_media me ON m.id = me.objectid GROUP BY m.classification;"
}

# -----------------------
# Query Selector
# -----------------------
choice = st.selectbox("📌 Pick a predefined query:", list(queries.keys()))

if st.button("Run Predefined Query"):
    sql = queries[choice]
    df = run_query(sql)
    st.write(f"### Results for: {choice}")
    st.dataframe(df)

# -----------------------
# Custom SQL Query
# -----------------------
st.subheader("📝 Write Your Own SQL")
user_query = st.text_area("Enter SQL query here:")

if st.button("Run Custom SQL"):
    try:
        df = run_query(user_query)
        st.write("### Custom Query Results")
        st.dataframe(df)
    except Exception as e:
        st.error(f"❌ Error: {e}")
