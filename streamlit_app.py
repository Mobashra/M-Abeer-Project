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
# 2. CONTROLS
# ======================================================
with st.container():
    c1, c2, c3 = st.columns([1, 2, 1])

    with c1:
        data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)

    with c2:
        # --- CALENDAR DATE RANGE SELECTOR ---
        st.write(" **Select Time Interval:**")
        # Default to the entire year of 2023
        default_start = date(2023, 1, 1)
        default_end = date(2023, 12, 31)
        
        date_range = st.date_input(
            "Select Range",
            value=(default_start, default_end),
            min_value=date(2021, 1, 1),
            max_value=date(2024, 12, 31),
            format="DD.MM.YYYY",
            label_visibility="collapsed"
        )

        # Handle case where user selects only one date (start) but not end yet
        if len(date_range) == 2:
            start_d, end_d = date_range
        else:
            start_d, end_d = date_range[0], date_range[0]

    with c3:
        # Group Selector Logic
        groups = (
            ["hydro", "wind", "thermal", "solar", "other"]
            if data_type == "Production"
            else ["cabin", "household", "primary", "secondary", "tertiary"]
        )
        idx = 0
        if "last_group" in st.session_state and st.session_state["last_group"] in groups:
            idx = groups.index(st.session_state["last_group"])
            
        selected_group = st.selectbox(f"{data_type} Group", groups, index=idx)
        st.session_state["last_group"] = selected_group

# ======================================================
# 3. LOAD DATA
# ======================================================
with st.spinner(f"Loading {selected_group} data..."):
    # 1. Price Area Data (Using NEW date range logic)
    df = utils.load_map_stats(start_d, end_d, data_type, selected_group)
    
    # 2. Map Geometries
    geojson_areas = utils.load_geojson()
    geojson_munis = utils.load_municipality_geojson()

if not geojson_areas:
    st.error("Error: 'elspot_areas.geojson' not found.")
    st.stop()

if not df.empty:
    df["price_area_map"] = df["price_area"].astype(str).str.replace("NO", "NO ")

# ======================================================
# 4. CHOROPLETH MAP SETUP
# ======================================================
st.subheader(f"Average {selected_group.capitalize()} {data_type}")

feature_key = "properties.ElSpotOmr"

# --- BASE LAYER: PRICE AREAS ---
if not df.empty:
    fig = px.choropleth_mapbox(
        df,
        geojson=geojson_areas,
        locations="price_area_map",
        featureidkey=feature_key,
        color="avg_value",
        color_continuous_scale="Viridis",
        mapbox_style="carto-positron",
        # ZOOM & CENTER TWEAKED FOR SCREEN FIT
        zoom=4.2, 
        center={"lat": 64.5, "lon": 16}, 
        opacity=0.6,
        labels={"avg_value": "MWh"}
    )
else:
    # Fallback outline
    fig = px.choropleth_mapbox(
        geojson=geojson_areas,
        locations=["NO 1", "NO 2", "NO 3", "NO 4", "NO 5"],
        featureidkey=feature_key,
        mapbox_style="carto-positron",
        zoom=4.2,
        center={"lat": 64.5, "lon": 16},
        opacity=0.3
    )

# --- BONUS: MUNICIPALITY OVERLAY TOGGLE ---
show_munis = st.toggle("🔍 Show Municipalities (Detailed Grid)", value=False)

if show_munis:
    if geojson_munis:
        # VISIBILITY FIX: Thicker lines and distinct color
        fig.add_trace(go.Choroplethmapbox(
            geojson=geojson_munis,
            locations=[f['properties'].get('nummer', i) for i, f in enumerate(geojson_munis['features'])],
            featureidkey="properties.nummer", 
            z=[1] * len(geojson_munis['features']),
            # Use a faint grey fill so you notice them, but keep transparency high
            colorscale=[[0, 'rgba(0,0,0,0.1)'], [1, 'rgba(0,0,0,0.1)']], 
            marker_line_color='black', # Darker border for visibility
            marker_line_width=1.0,     # Thicker line (was 0.5)
            showscale=False,
            hoverinfo='skip',
            name="Municipalities"
        ))
    else:
        st.warning("⚠️ Municipality file not found.")

# --- HIGHLIGHT SELECTED AREA (Red Outline) ---
highlight_name = current_area.replace("NO", "NO ")
fig.add_trace(go.Choroplethmapbox(
    geojson=geojson_areas,
    locations=[highlight_name],
    featureidkey=feature_key,
    z=[1],
    colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
    marker_line_color="red",
    marker_line_width=4,
    showscale=False,
    hoverinfo="skip",
    name="Selected Area"
))

# SCREEN FIT: Fixed height to fill standard laptop screen better
fig.update_layout(
    margin=dict(r=0, t=0, l=0, b=0), 
    clickmode='event+select',
    height=600 
)

# ======================================================
# 5. INTERACTION HANDLER
# ======================================================
event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

if event and "selection" in event and event["selection"]["points"]:
    point = event["selection"]["points"][0]

    # Update Coordinates
    if "lat" in point:
        st.session_state["selected_coords"] = {"lat": point["lat"], "lon": point["lon"]}

    # Update Area (Handle Price Area Click Only)
    if "location" in point:
        clicked = point["location"].replace(" ", "")
        # Filter out municipality clicks (usually numbers) vs Price Areas (NO1..)
        if clicked in utils.CITIES and clicked != current_area:
            st.session_state["selected_price_area"] = clicked
            city = utils.CITIES[clicked]
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

# ======================================================
# 6. FOOTER
# ======================================================
st.success(f"✅ Active Region: {st.session_state['selected_price_area']} "
           f"({st.session_state['selected_coords']['lat']:.4f}, {st.session_state['selected_coords']['lon']:.4f})")