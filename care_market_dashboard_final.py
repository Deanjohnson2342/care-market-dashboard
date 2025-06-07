import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

# --- LFA Banner ---
st.markdown(
    """
    <div style='text-align: center; margin-bottom: 30px;'>
        <h1 style='color: red; font-size: 64px;'>LFA</h1>
        <div style='font-size: 48px;'>❤️</div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Load from Google Sheets ---
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1iz-rjfmBNkfBj4KUxLWBHwaqTOvtfmbu/export?format=xlsx"
    df = pd.read_excel(url, sheet_name="HSCA_Active_Locations")
    df["Care homes beds"] = pd.to_numeric(df["Care homes beds"], errors='coerce')
    df["Publication Date"] = pd.to_datetime(df["Publication Date"], errors='coerce')
    return df.dropna(subset=["Brand Name", "Care homes beds", "Location Inspection Directorate"])

df = load_data()
df = df[df["Location Inspection Directorate"] == "Adult social care"]

# --- Sidebar filters ---
st.sidebar.header("🔍 Filters")

brands = sorted(df["Brand Name"].dropna().unique())
selected_brand = st.sidebar.selectbox("Select a Brand (optional)", ["All"] + brands)

las = sorted(df["Location Local Authority"].dropna().unique())
selected_la = st.sidebar.selectbox("Select Local Authority (optional)", ["All"] + las)

valid_beds = df["Care homes beds"].dropna()
min_beds = int(valid_beds.min()) if not valid_beds.empty else 0
max_beds = int(valid_beds.max()) if not valid_beds.empty else 100
bed_range = st.sidebar.slider("Filter by Bed Count", min_beds, max_beds, (min_beds, max_beds))

ratings = df["Location Latest Overall Rating"].dropna().unique()
selected_ratings = st.sidebar.multiselect("Filter by Rating", options=ratings, default=list(ratings))

# --- Apply filters ---
filtered = df.copy()
if selected_brand != "All":
    filtered = filtered[filtered["Brand Name"] == selected_brand]
if selected_la != "All":
    filtered = filtered[filtered["Location Local Authority"] == selected_la]
filtered = filtered[
    (filtered["Care homes beds"].between(bed_range[0], bed_range[1])) &
    (filtered["Location Latest Overall Rating"].isin(selected_ratings))
]

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["🏢 Brand Overview", "⭐ Ratings", "📅 Inspection Activity", "🗺️ Map View"])

# --- Brand Overview ---
with tab1:
    st.title("🏢 Brand & Provider Overview")

    st.metric("Total Beds", f"{int(filtered['Care homes beds'].sum()):,}")
    st.metric("Total Providers", filtered["Provider Name"].nunique())
    st.metric("Total Locations", filtered["Location ID"].nunique())

    st.subheader("Provider Segmentation by Bed Count")
    provider_beds = filtered.groupby("Provider Name")["Care homes beds"].sum().reset_index()
    st.write(f"🔹 Providers ≤ 20 beds: {len(provider_beds[provider_beds['Care homes beds'] <= 20])}")
    st.write(f"🔹 Providers 21–100 beds: {len(provider_beds[(provider_beds['Care homes beds'] > 20) & (provider_beds['Care homes beds'] <= 100)])}")
    st.write(f"🔹 Providers > 100 beds: {len(provider_beds[provider_beds['Care homes beds'] > 100])}")

    st.subheader("Top 10 Brands by Bed Share")
    top_brands = df.groupby("Brand Name")["Care homes beds"].sum().reset_index()
    top_brands["Market Share (%)"] = 100 * top_brands["Care homes beds"] / df["Care homes beds"].sum()
    st.dataframe(top_brands.sort_values("Care homes beds", ascending=False).head(10))

# --- Ratings ---
with tab2:
    st.title("⭐ Rating Overview")
    rating_counts = filtered["Location Latest Overall Rating"].value_counts().to_frame().reset_index()
    rating_counts.columns = ["Rating", "Count"]
    rating_counts["%"] = 100 * rating_counts["Count"] / rating_counts["Count"].sum()
    st.dataframe(rating_counts)

    st.metric("% Good", f"{rating_counts[rating_counts['Rating']=='Good']['%'].values[0]:.1f}%" if 'Good' in rating_counts['Rating'].values else "N/A")
    st.metric("% Outstanding", f"{rating_counts[rating_counts['Rating']=='Outstanding']['%'].values[0]:.1f}%" if 'Outstanding' in rating_counts['Rating'].values else "N/A")

# --- Inspection Activity ---
with tab3:
    st.title("📅 Recent Inspection Activity")
    inspections = filtered.dropna(subset=["Publication Date"])
    inspections_by_month = inspections["Publication Date"].dt.to_period("M").value_counts().sort_index()
    inspections_df = inspections_by_month.reset_index()
    inspections_df.columns = ["Month", "Inspection Count"]
    st.line_chart(inspections_df.set_index("Month"))

# --- Map View ---
with tab4:
    st.title("🗺️ Map of Locations")

    m = folium.Map(location=[52.5, -1.5], zoom_start=6)
    for _, row in filtered.iterrows():
        if pd.notna(row["Location Latitude"]) and pd.notna(row["Location Longitude"]):
            folium.CircleMarker(
                location=[row["Location Latitude"], row["Location Longitude"]],
                radius=min(row["Care homes beds"] / 10, 10),
                color="blue",
                fill=True,
                fill_opacity=0.6,
                popup=f"{row['Location Name']}<br>Beds: {row['Care homes beds']}"
            ).add_to(m)
    st_folium(m, width=900, height=600)



