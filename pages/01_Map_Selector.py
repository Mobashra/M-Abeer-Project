import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import utils
from datetime import date

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Map Selector", layout="wide")

# Render Sidebar Colors & Info
utils.render_sidebar()

st.title("🇳🇴 Regional Energy Overview")

# ======================================================
# 1. INIT STATE
# ======================================================
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

current_area = st.session_state["selected_price_area"]

# ======================================================
# 2. CONTROLS (5 Columns - Dashboard Style)
# ======================================================
with st.container():
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown("###### 1. Source")
        data_type = st.radio("Source", ["Production", "Consumption"], horizontal=True, label_visibility="collapsed")

    with c2:
        st.markdown("###### 2. Start Date")
        start_d = st.date_input("Start", date(2021, 1, 1), min_value=date(2021, 1, 1), max_value=date(2024, 12, 31), label_visibility="collapsed")

    with c3:
        st.markdown("###### 3. End Date")
        end_d = st.date_input("End", date(2021, 12, 31), min_value=date(2021, 1, 1), max_value=date(2024, 12, 31), label_visibility="collapsed")

    with c4:
        st.markdown("###### 4. Group")
        groups = ["hydro", "wind", "thermal", "solar", "other"] if data_type == "Production" else ["cabin", "household", "primary", "secondary", "tertiary"]
        selected_group = st.selectbox("Group", groups, index=0, label_visibility="collapsed")

    with c5:
        st.markdown("###### 5. Region")
        area_list = sorted(utils.CITIES.keys())
        manual_area = st.selectbox("Region", area_list, index=area_list.index(current_area), label_visibility="collapsed")
        
        if manual_area != current_area:
            st.session_state["selected_price_area"] = manual_area
            city = utils.CITIES[manual_area]
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

    if start_d > end_d:
        st.error("Start Date must be before End Date.")
        st.stop()

st.divider()

# ======================================================
# 3. LOAD DATA
# ======================================================
with st.spinner("Loading Map Data..."):
    df = utils.load_map_stats(start_d, end_d, data_type, selected_group)
    geojson_areas = utils.load_geojson()
    geojson_munis = utils.load_municipality_geojson()

if not geojson_areas:
    st.error("Error: 'elspot_areas.geojson' not found.")
    st.stop()

if not df.empty:
    # Create 'price_area_map' column (NO1 -> NO 1) for proper mapping/labelling
    df["price_area_map"] = df["price_area"].astype(str).str.replace("NO", "NO ")

# ======================================================
# 4. MAP VISUALIZATION
# ======================================================
# Layout: 3 parts Map, 1 part Info (Longer & Narrower Map)
c_map, c_info = st.columns([3, 1])

with c_map:
    # Toggle for Bonus
    show_munis = st.toggle("🔍 Show Municipalities (Bonus)", value=False)

    feature_key = "properties.ElSpotOmr"

    # --- LAYER 1: BASE MAP (With Labels Restored) ---
    if not df.empty:
        fig = px.choropleth_mapbox(
            df,
            geojson=geojson_areas,
            locations="price_area_map", # Matches 'NO 1'
            featureidkey=feature_key,   # Matches GeoJSON
            color="avg_value",
            color_continuous_scale="Viridis",
            mapbox_style="carto-positron",
            zoom=4.5, 
            center={"lat": 65.0, "lon": 16.0}, 
            opacity=0.6,
            labels={"avg_value": "MWh", "price_area_map": "Region"},
            hover_name="price_area_map", # <--- THIS RESTORES THE LABELS (NO 1, NO 2)
            hover_data={"price_area_map": False, "avg_value": ":.2f"}
        )
    else:
        # Fallback
        fig = px.choropleth_mapbox(
            geojson=geojson_areas,
            locations=["NO 1", "NO 2", "NO 3", "NO 4", "NO 5"],
            featureidkey=feature_key,
            mapbox_style="carto-positron",
            zoom=4.5,
            center={"lat": 65.0, "lon": 16.0},
            opacity=0.3
        )

    # --- LAYER 2: MUNICIPALITIES (Overlay) ---
    if show_munis and geojson_munis:
        first = geojson_munis['features'][0]['properties']
        muni_key = "properties.nummer" if 'nummer' in first else ("properties.kommunenummer" if 'kommunenummer' in first else "properties.id")
        
        if muni_key:
            prop = muni_key.split('.')[1]
            locs = [f['properties'].get(prop) for f in geojson_munis['features']]
            
            fig.add_trace(go.Choroplethmapbox(
                geojson=geojson_munis,
                locations=locs,
                featureidkey=muni_key,
                z=[1] * len(locs),
                colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']],
                marker_line_color='rgba(20, 20, 20, 0.8)', # Visible Black Lines
                marker_line_width=0.8,
                showscale=False,
                hoverinfo='skip', # Pass clicks to price area
                name="Municipalities"
            ))

    # --- LAYER 3: HIGHLIGHT ---
    hl_name = st.session_state["selected_price_area"].replace("NO", "NO ")
    fig.add_trace(go.Choroplethmapbox(
        geojson=geojson_areas,
        locations=[hl_name],
        featureidkey=feature_key,
        z=[1],
        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
        marker_line_color="red",
        marker_line_width=4,
        showscale=False,
        hoverinfo="skip",
        name="Selected"
    ))

    # Taller Layout (800px)
    fig.update_layout(
        margin=dict(r=0, t=0, l=0, b=0), 
        clickmode='event+select',
        height=800, 
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )

    # --- RENDER ---
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

    # --- INTERACTION (Background Updates) ---
    if event and "selection" in event and event["selection"]["points"]:
        point = event["selection"]["points"][0]
        
        # 1. Coordinates (Always update, needed for weather page)
        if "lat" in point:
            st.session_state["selected_coords"] = {"lat": point["lat"], "lon": point["lon"]}
            # Bonus: Fetch Elevation
            elev = utils.fetch_elevation(point["lat"], point["lon"])
            if elev: st.session_state["elevation"] = elev
        
        # 2. Region (Only if clicked price area)
        if "location" in point:
            clicked = point["location"].replace(" ", "")
            if clicked in utils.CITIES and clicked != st.session_state["selected_price_area"]:
                st.session_state["selected_price_area"] = clicked
                city = utils.CITIES[clicked]
                # Update coords to city center if switching region via map
                st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
                st.rerun()

with c_info:
    st.info(f"""
    **Active Region**
    # {st.session_state['selected_price_area']}
    
    **Clicked Coordinates**
    {st.session_state['selected_coords']['lat']:.4f}, {st.session_state['selected_coords']['lon']:.4f}
    """)
    
    if "elevation" in st.session_state:
        st.metric("⛰️ Elevation", f"{st.session_state['elevation']} m")

    st.caption("Use the map to select a region for analysis.")