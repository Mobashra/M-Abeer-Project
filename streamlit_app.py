import streamlit as st
import plotly.express as px
import pandas as pd
import utils

st.set_page_config(page_title="Norwegian Energy Atlas", layout="wide")

st.title("🇳🇴 Regional Energy Overview")
st.info("Select a region on the map to set the location for Snow Drift & Weather Analysis.")

# --- 1. INITIALIZE SESSION STATE ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
if "selected_coords" not in st.session_state:
    st.session_state["selected_coords"] = utils.CITIES["NO1"]

# --- 2. CONTROLS (Moved to Top!) ---
# We need these values BEFORE we load the data to make the query fast.
col1, col2, col3 = st.columns(3)

with col1:
    # Manual Area Selector (Syncs with Map)
    all_areas = sorted(list(utils.CITIES.keys()))
    selected_area_state = st.session_state["selected_price_area"]
    
    # Safety check: ensure state value is in list
    idx = all_areas.index(selected_area_state) if selected_area_state in all_areas else 0
    
    selected_area = st.selectbox("Select Analysis Region:", options=all_areas, index=idx)
    
    # Update state if changed manually
    if selected_area != st.session_state["selected_price_area"]:
        st.session_state["selected_price_area"] = selected_area
        st.session_state["selected_coords"] = utils.CITIES[selected_area]
        st.rerun()

with col2:
    # Hardcoded list is faster than querying DB for unique values first
    prod_groups = ["hydro", "wind", "nuclear", "solar", "thermal", "other"]
    selected_group = st.selectbox("Map Production Group:", prod_groups, index=0)

with col3:
    days = st.slider("Days to Aggregate", 7, 365, 30)

# --- 3. LOAD DATA (Optimized) ---
# Now we pass the inputs to the loader so it only fetches what is needed
with st.spinner(f"Fetching last {days} days of {selected_group} data..."):
    df = utils.load_map_data(days_back=days, selected_group=selected_group)
    geojson = utils.load_geojson()

if df.empty:
    st.error(f"No data found for **{selected_group}** in the last **{days}** days.")
    st.stop()

if not geojson:
    st.error("GeoJSON file not found.")
    st.stop()

# --- 4. MAP PREPARATION ---
# Aggregate mean value per area
df_map = df.groupby('price_area')['production_mwh'].mean().reset_index()

# FIX: Match GeoJSON "NO 1" format with Data "NO1" format
df_map['price_area_map'] = df_map['price_area'].str.replace("NO", "NO ")

st.subheader(f"Average {selected_group.capitalize()} Production (Last {days} Days)")

fig = px.choropleth_mapbox(
    df_map, 
    geojson=geojson, 
    locations='price_area_map', 
    featureidkey="properties.ElSpotOmr", # Matches "NO 1" in NVE GeoJSON
    color='production_mwh', 
    color_continuous_scale="Viridis", 
    mapbox_style="carto-positron",
    zoom=4, 
    center={"lat": 65, "lon": 15}, 
    opacity=0.5,
    labels={'production_mwh': 'MWh'}
)
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

# --- 5. CLICK INTERACTION ---
event = st.plotly_chart(fig, on_select="rerun", selection_mode="points", use_container_width=True, key="map")

if event and event["selection"]["points"]:
    point = event["selection"]["points"][0]
    
    # 1. Update Coordinates (Lat/Lon click)
    if "lat" in point:
        new_coords = {"lat": point["lat"], "lon": point["lon"]}
        st.session_state["selected_coords"] = new_coords
    
    # 2. Update Price Area (Polygon click)
    if "location" in point:
        # Convert "NO 1" back to "NO1"
        area_clicked = point["location"].replace(" ", "")
        if area_clicked in utils.CITIES:
            st.session_state["selected_price_area"] = area_clicked
            st.session_state["selected_coords"] = utils.CITIES[area_clicked]
            st.rerun()

# --- 6. FOOTER STATUS ---
curr_area = st.session_state["selected_price_area"]
curr_lat = st.session_state["selected_coords"]["lat"]
curr_lon = st.session_state["selected_coords"]["lon"]

st.success(f"✅ **Active Location:** {curr_area} ({curr_lat:.4f}, {curr_lon:.4f}) — Ready for Analysis pages!")