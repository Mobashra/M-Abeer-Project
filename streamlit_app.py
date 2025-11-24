import streamlit as st
import plotly.express as px
import pandas as pd
import utils

st.set_page_config(page_title="Norwegian Energy Atlas", layout="wide")

st.title("🇳🇴 Regional Energy Overview")
st.info("Select a region on the map to set the location for Snow Drift & Weather Analysis.")

# 1. Load Data
with st.spinner("Loading data..."):
    df = utils.load_map_data()
    geojson = utils.load_geojson()

# --- DEBUGGING BLOCK (Add this!) ---
if df.empty:
    st.error("❌ **CRITICAL ERROR:** Production Data is empty.")
    st.write("Possible reasons:")
    st.write("1. MongoDB connection failed (Check `.streamlit/secrets.toml`).")
    st.write("2. The database collection is empty.")
    st.write("3. `utils.py` is not filtering the data correctly.")

if not geojson:
    st.error("❌ **CRITICAL ERROR:** GeoJSON file not found.")
    st.write("Make sure `elspot_areas.geojson` is inside the main project folder (next to Home.py).")

# Stop only after showing the error
if df.empty or not geojson:
    st.stop()
# -----------------------------------

# 2. Controls (The rest of your code continues here...)

# 2. Controls
col1, col2 = st.columns(2)
with col1:
    prod_groups = df['production_group'].unique()
    selected_group = st.selectbox("Map Production Group:", prod_groups)
with col2:
    days = st.slider("Days to Aggregate (from latest date)", 7, 365, 30)



# 3. Map Logic
max_date = df['date'].max()
mask = (df['date'] >= max_date - pd.Timedelta(days=days)) & (df['production_group'] == selected_group)
df_map = df[mask].groupby('price_area')['production_mwh'].mean().reset_index()

# --- CRITICAL FIX START ---
# Your GeoJSON has "NO 1", "NO 2"... but DataFrame has "NO1", "NO2"...
# We must insert a space into the DataFrame values to match the GeoJSON exactly.
df_map['price_area_map'] = df_map['price_area'].str.replace("NO", "NO ")
# --- CRITICAL FIX END ---

st.subheader(f"Average {selected_group} Production (Last {days} Days)")

fig = px.choropleth_mapbox(
    df_map, 
    geojson=geojson, 
    locations='price_area_map', # Use the new column with the space
    featureidkey="properties.ElSpotOmr", # Updated to match your JSON key
    color='production_mwh', 
    color_continuous_scale="Viridis", 
    mapbox_style="carto-positron",
    zoom=4, 
    center={"lat": 65, "lon": 15}, 
    opacity=0.5
)
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})



# 4. Capture Click
event = st.plotly_chart(fig, on_select="rerun", selection_mode="points", use_container_width=True)

if event and event["selection"]["points"]:
    point = event["selection"]["points"][0]
    
    # Save Lat/Lon if clicked
    if "lat" in point:
        st.session_state["selected_coords"] = {"lat": point["lat"], "lon": point["lon"]}
        st.success(f"Selected Coordinates: {point['lat']:.4f}, {point['lon']:.4f}")
    
    # Save Price Area if clicked
    if "location" in point:
        st.session_state["selected_price_area"] = point["location"]
        st.success(f"Selected Price Area: {point['location']}")

# Default fallback if nothing selected
if "selected_price_area" not in st.session_state:
    st.info("Please click on the map to select a region.")