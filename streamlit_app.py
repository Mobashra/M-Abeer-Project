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
# 2. CONTROLS (Top Bar)
# ======================================================
with st.container():
    # Use 4 columns for a cleaner "Dashboard" look
    c1, c2, c3, c4 = st.columns([1.5, 2, 1.5, 1.5])

    with c1:
        st.markdown("##### 1. Data Source")
        data_type = st.radio("Source", ["Production", "Consumption"], horizontal=True, label_visibility="collapsed")

    with c2:
        st.markdown("##### 2. Time Period")
        # Default to 2023
        default_start = date(2023, 1, 1)
        default_end = date(2023, 12, 31)
        
        # Calendar Range Picker
        date_range = st.date_input(
            "Select Date Range",
            value=(default_start, default_end),
            min_value=date(2021, 1, 1),
            max_value=date(2024, 12, 31),
            format="DD.MM.YYYY", # Nice European format
            label_visibility="collapsed"
        )

        # Safety logic for date range
        if len(date_range) == 2:
            start_d, end_d = date_range
        else:
            start_d, end_d = date_range[0], date_range[0]

    with c3:
        st.markdown(f"##### 3. {data_type} Group")
        groups = (
            ["hydro", "wind", "thermal", "solar", "other"]
            if data_type == "Production"
            else ["cabin", "household", "primary", "secondary", "tertiary"]
        )
        # Preserve previous selection if possible
        idx = 0
        if "last_group" in st.session_state and st.session_state["last_group"] in groups:
            idx = groups.index(st.session_state["last_group"])
            
        selected_group = st.selectbox("Group", groups, index=idx, label_visibility="collapsed")
        st.session_state["last_group"] = selected_group

    with c4:
        st.markdown("##### 4. Region (Fallback)")
        # This Dropdown works even if Map Click fails
        area_list = sorted(utils.CITIES.keys())
        manual_area = st.selectbox(
            "Select Area", 
            area_list, 
            index=area_list.index(current_area),
            label_visibility="collapsed"
        )
        
        # Handle Manual Selection Update
        if manual_area != current_area:
            st.session_state["selected_price_area"] = manual_area
            city = utils.CITIES[manual_area]
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

# ======================================================
# 3. LOAD DATA
# ======================================================
with st.spinner(f"Loading {selected_group} data..."):
    # Load Stats based on Calendar Dates
    df = utils.load_map_stats(start_d, end_d, data_type, selected_group)
    
    # Load Geometries
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
st.divider()
c_map, c_info = st.columns([3, 1])

with c_map:
    st.caption(f"Map showing average **{selected_group}** ({data_type}) from **{start_d}** to **{end_d}**.")
    
    # Toggle for Bonus Content
    show_munis = st.checkbox("🔍 Enable Detailed View (Show Municipalities)", value=False)

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

    # --- BONUS: MUNICIPALITY OVERLAY ---
    if show_munis and geojson_munis:
        fig.add_trace(go.Choroplethmapbox(
            geojson=geojson_munis,
            locations=[f['properties'].get('nummer', i) for i, f in enumerate(geojson_munis['features'])],
            featureidkey="properties.nummer", 
            z=[1] * len(geojson_munis['features']),
            colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']], # Fully Transparent Fill
            marker_line_color='rgba(50, 50, 50, 0.6)', # Dark Grey, semi-transparent lines
            marker_line_width=0.8,
            showscale=False,
            hoverinfo='skip',
            name="Municipalities"
        ))

    # --- HIGHLIGHT SELECTED AREA ---
    highlight_name = st.session_state["selected_price_area"].replace("NO", "NO ")
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

    # ADJUST MAP SIZE HERE
    fig.update_layout(
        margin=dict(r=0, t=0, l=0, b=0), 
        clickmode='event+select',
        height=500, # <--- Adjusted Height (Smaller)
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )

    # INTERACTION
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

    if event and "selection" in event and event["selection"]["points"]:
        point = event["selection"]["points"][0]
        if "lat" in point:
            st.session_state["selected_coords"] = {"lat": point["lat"], "lon": point["lon"]}
        if "location" in point:
            clicked = point["location"].replace(" ", "")
            if clicked in utils.CITIES and clicked != st.session_state["selected_price_area"]:
                st.session_state["selected_price_area"] = clicked
                city = utils.CITIES[clicked]
                st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
                st.rerun()

with c_info:
    # Contextual Info Box
    st.info(f"""
    **Current Selection**
    
    Region: **{st.session_state['selected_price_area']}**
    
    Coordinates:
    {st.session_state['selected_coords']['lat']:.4f}, {st.session_state['selected_coords']['lon']:.4f}
    """)
    
    st.success("✅ Map & Data Loaded")
    st.caption("Use the 'Select Area' dropdown above if map clicking is difficult.")