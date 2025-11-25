import streamlit as st
import plotly.express as px
import pandas as pd
import utils

st.set_page_config(page_title="Norwegian Energy Atlas", layout="wide")

st.title("🇳🇴 Regional Energy Overview")
st.info("Select Data Type, Year, and Region to set the context for analysis.")

# --- 1. INITIALIZE SESSION STATE ---
# We set defaults so other pages don't crash if visited first
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

if "selected_coords" not in st.session_state:
    # Use the consistent lat/lon keys from utils.CITIES
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

# --- 2. CONTROLS (Global) ---
# We place controls BEFORE loading data to optimize the database query

# Row 1: Broad Selection
c1, c2, c3 = st.columns(3)
with c1:
    # Toggle between Production and Consumption
    data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
with c2:
    # Year Selector (Essential for viewing historical data)
    year = st.selectbox("Year", [2021, 2022, 2023, 2024], index=3)
with c3:
    # Days Slider (Relative to the selected year)
    days = st.slider(f"Days to Aggregate (Ending Dec 31, {year})", 7, 365, 30)

# Row 2: Specific Selection
c4, c5 = st.columns(2)
with c4:
    # Dynamic groups based on data type
    if data_type == "Production":
        groups = ["hydro", "wind", "thermal", "solar", "other"]
    else:
        # YOUR SPECIFIC CONSUMPTION GROUPS
        groups = ["cabin", "household", "primary", "secondary", "tertiary"]
        
    selected_group = st.selectbox(f"{data_type} Group:", groups, index=0)

with c5:
    # Manual Area Selector (Syncs with Map)
    all_areas = sorted(list(utils.CITIES.keys()))
    curr = st.session_state["selected_price_area"]
    # Safety check to find index
    idx = all_areas.index(curr) if curr in all_areas else 0
    
    selected_area = st.selectbox("Select Region (for Deep Dive):", all_areas, index=idx)
    
    # Sync manual selection to state immediately
    if selected_area != st.session_state["selected_price_area"]:
        st.session_state["selected_price_area"] = selected_area
        city = utils.CITIES[selected_area]
        st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
        st.rerun()

# --- 3. LOAD DATA ---
with st.spinner(f"Loading {selected_group} data for {year}..."):
    # We pass all filters to the loader to keep it fast
    df = utils.load_map_data(target_year=year, days_to_agg=days, data_type=data_type, selected_group=selected_group)
    geojson = utils.load_geojson()

if df.empty:
    st.warning(f"No data found for **{selected_group}** in **{year}**. Try selecting a different group or year.")
    st.stop()

if not geojson:
    st.error("GeoJSON file not found. Please ensure 'elspot_areas.geojson' is in the project folder.")
    st.stop()

# --- 4. MAP PREPARATION ---
# Aggregate mean value per price area
df_map = df.groupby('price_area')['val'].mean().reset_index()

# FIX: The GeoJSON uses "NO 1" but data uses "NO1". We add the space to match.
df_map['price_area_map'] = df_map['price_area'].str.replace("NO", "NO ")

st.subheader(f"Mean {selected_group.capitalize()} {data_type} ({year})")

fig = px.choropleth_mapbox(
    df_map, 
    geojson=geojson, 
    locations='price_area_map', 
    featureidkey="properties.ElSpotOmr", # This matches the key in your specific GeoJSON
    color='val', 
    color_continuous_scale="Viridis", 
    mapbox_style="carto-positron",
    zoom=4.5, 
    center={"lat": 64, "lon": 12}, 
    opacity=0.5,
    labels={'val': 'MWh'}
)
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

# --- 5. CLICK INTERACTION ---
# Display the map and capture clicks
event = st.plotly_chart(fig, on_select="rerun", selection_mode="points", use_container_width=True)

if event and event["selection"]["points"]:
    point = event["selection"]["points"][0]
    
    # 1. Update Coordinates (if Lat/Lon available)
    if "lat" in point:
        st.session_state["selected_coords"] = {"lat": point["lat"], "lon": point["lon"]}
    
    # 2. Update Price Area (if Polygon clicked)
    if "location" in point:
        # Convert "NO 1" back to "NO1" for our system
        area_clicked = point["location"].replace(" ", "")
        
        # Only update if valid area and different from current
        if area_clicked in utils.CITIES and area_clicked != st.session_state["selected_price_area"]:
            st.session_state["selected_price_area"] = area_clicked
            city = utils.CITIES[area_clicked]
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

# --- 6. FOOTER STATUS ---
curr_area = st.session_state["selected_price_area"]
curr_lat = st.session_state["selected_coords"]["lat"]
curr_lon = st.session_state["selected_coords"]["lon"]

st.success(f"✅ **Active Location:** {curr_area} ({curr_lat:.4f}, {curr_lon:.4f}) — Ready for Analysis pages!")