import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import utils
from datetime import date

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Norwegian Energy Atlas", layout="wide")
st.title("🇳🇴 Regional Energy Overview")

# ======================================================
# 1. INIT SESSION STATE
# ======================================================
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

if "selected_coords" not in st.session_state:
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

current_area = st.session_state["selected_price_area"]

# ======================================================
# 2. SIDEBAR CONTROLS (Best for Vertical Maps)
# ======================================================
with st.sidebar:
    st.header("Global Filters")
    
    # --- A. Data Source ---
    data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
    
    # --- B. Date Range (2021-2024) ---
    st.subheader("Time Period")
    # Default to a recent window
    default_start = date(2023, 1, 1)
    default_end = date(2023, 12, 31)
    
    date_range = st.date_input(
        "Select Interval",
        value=(default_start, default_end),
        min_value=date(2021, 1, 1),
        max_value=date(2024, 12, 31),
        format="DD.MM.YYYY"
    )

    # Handle single date selection safety
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
    else:
        # Fallback if user picks only start date
        start_d = date_range[0] if isinstance(date_range, tuple) and date_range else default_start
        end_d = start_d

    # --- C. Group Selector ---
    st.subheader("Energy Group")
    groups = (
        ["hydro", "wind", "thermal", "solar", "other"]
        if data_type == "Production"
        else ["cabin", "household", "primary", "secondary", "tertiary"]
    )
    
    idx = 0
    if "last_group" in st.session_state and st.session_state["last_group"] in groups:
        idx = groups.index(st.session_state["last_group"])
        
    selected_group = st.selectbox("Group", groups, index=idx)
    st.session_state["last_group"] = selected_group

    st.divider()
    
    # --- D. Region Fallback ---
    st.subheader("Manual Selection")
    area_list = sorted(utils.CITIES.keys())
    manual_area = st.selectbox(
        "Select Region", 
        area_list, 
        index=area_list.index(current_area)
    )
    
    if manual_area != current_area:
        st.session_state["selected_price_area"] = manual_area
        city = utils.CITIES[manual_area]
        st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
        st.rerun()

    # --- E. Map Settings ---
    st.divider()
    st.caption("Map Settings")
    show_munis = st.toggle("Show Municipalities", value=False)

# ======================================================
# 3. LOAD DATA
# ======================================================
with st.spinner(f"Loading {selected_group} data..."):
    df = utils.load_map_stats(start_d, end_d, data_type, selected_group)
    geojson_areas = utils.load_geojson()
    geojson_munis = utils.load_municipality_geojson()

if not geojson_areas:
    st.error("❌ 'elspot_areas.geojson' not found.")
    st.stop()

if not df.empty:
    df["price_area_map"] = df["price_area"].astype(str).str.replace("NO", "NO ")

# ======================================================
# 4. MAP VISUALIZATION
# ======================================================
# Main area is now dedicated entirely to the map
st.markdown(f"### 🗺️ Mean {selected_group.capitalize()} ({start_d} — {end_d})")

# Feature Key for Price Areas
feature_key = "properties.ElSpotOmr"

# --- BASE LAYER ---
if not df.empty:
    fig = px.choropleth_mapbox(
        df,
        geojson=geojson_areas,
        locations="price_area_map",
        featureidkey=feature_key,
        color="avg_value",
        color_continuous_scale="Viridis",
        mapbox_style="carto-positron",
        zoom=4.5, 
        center={"lat": 65.0, "lon": 15.0}, 
        opacity=0.6,
        labels={"avg_value": "MWh"}
    )
else:
    fig = px.choropleth_mapbox(
        geojson=geojson_areas,
        locations=["NO 1", "NO 2", "NO 3", "NO 4", "NO 5"],
        featureidkey=feature_key,
        mapbox_style="carto-positron",
        zoom=4.5,
        center={"lat": 65.0, "lon": 15.0},
        opacity=0.3
    )

# --- BONUS: MUNICIPALITY OVERLAY ---
if show_munis:
    if geojson_munis:
        # AUTO-DETECT KEY LOGIC
        first_props = geojson_munis['features'][0]['properties']
        
        # Try common keys
        if 'nummer' in first_props:
            muni_key = "properties.nummer"
            muni_ids = [f['properties']['nummer'] for f in geojson_munis['features']]
        elif 'kommunenummer' in first_props:
            muni_key = "properties.kommunenummer"
            muni_ids = [f['properties']['kommunenummer'] for f in geojson_munis['features']]
        elif 'id' in first_props:
            muni_key = "properties.id"
            muni_ids = [f['properties']['id'] for f in geojson_munis['features']]
        else:
            muni_key = None
            
        if muni_key:
            fig.add_trace(go.Choroplethmapbox(
                geojson=geojson_munis,
                locations=muni_ids,
                featureidkey=muni_key,
                z=[1] * len(muni_ids),
                colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']], 
                marker_line_color='black', # HIGH CONTRAST
                marker_line_width=1.5,     # THICK LINE
                showscale=False,
                hoverinfo='text',
                # Try to show name
                text=[f['properties'].get('navn', [{}])[0].get('navn', 'Muni') if isinstance(f['properties'].get('navn'), list) else f['properties'].get('navn', 'Muni') for f in geojson_munis['features']],
                name="Municipalities"
            ))
        else:
            # DEBUGGER: Show user what keys exist if we failed
            st.warning("⚠️ Could not detect ID key. See Debug info below.")
            with st.expander("Debug: GeoJSON Properties"):
                st.write(first_props)
    else:
        st.warning("⚠️ Municipality GeoJSON file missing.")

# --- HIGHLIGHT SELECTED AREA ---
highlight_name = st.session_state["selected_price_area"].replace("NO", "NO ")
fig.add_trace(go.Choroplethmapbox(
    geojson=geojson_areas,
    locations=[highlight_name],
    featureidkey=feature_key,
    z=[1],
    colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
    marker_line_color="red",
    marker_line_width=3,
    showscale=False,
    hoverinfo="skip",
    name="Selected"
))

# TALL MAP FOR NORWAY
fig.update_layout(
    margin=dict(r=0, t=0, l=0, b=0), 
    clickmode='event+select',
    height=800, # <--- TALL HEIGHT
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.8)")
)

# INTERACTION
event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

if event and "selection" in event and event["selection"]["points"]:
    point = event["selection"]["points"][0]
    
    # 1. Capture Lat/Lon (Always works)
    if "lat" in point:
        st.session_state["selected_coords"] = {"lat": point["lat"], "lon": point["lon"]}
        
    # 2. Capture Region (Only if clicking price area)
    if "location" in point:
        clicked = point["location"].replace(" ", "")
        if clicked in utils.CITIES and clicked != st.session_state["selected_price_area"]:
            st.session_state["selected_price_area"] = clicked
            city = utils.CITIES[clicked]
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

# ======================================================
# 5. FOOTER INFO
# ======================================================
cols = st.columns(4)
cols[0].info(f"**Region:** {st.session_state['selected_price_area']}")
cols[1].info(f"**Lat:** {st.session_state['selected_coords']['lat']:.4f}")
cols[2].info(f"**Lon:** {st.session_state['selected_coords']['lon']:.4f}")