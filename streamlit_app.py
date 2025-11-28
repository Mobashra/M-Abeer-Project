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
# 2. TOP CONTROL BAR (5 Columns for Perfect Alignment)
# ======================================================
with st.container():
    # 5 Equal columns align widgets nicely
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown("###### 1. Source")
        data_type = st.radio(
            "Source", 
            ["Production", "Consumption"], 
            horizontal=True, 
            label_visibility="collapsed"
        )

    with c2:
        st.markdown("###### 2. Start Date")
        start_d = st.date_input(
            "Start",
            value=date(2021, 1, 1),
            min_value=date(2021, 1, 1),
            max_value=date(2024, 12, 31),
            format="DD.MM.YYYY",
            label_visibility="collapsed"
        )

    with c3:
        st.markdown("###### 3. End Date")
        end_d = st.date_input(
            "End",
            value=date(2021, 12, 31),
            min_value=date(2021, 1, 1),
            max_value=date(2024, 12, 31),
            format="DD.MM.YYYY",
            label_visibility="collapsed"
        )

    with c4:
        st.markdown(f"###### 4. Group")
        groups = (
            ["hydro", "wind", "thermal", "solar", "other"]
            if data_type == "Production"
            else ["cabin", "household", "primary", "secondary", "tertiary"]
        )
        idx = 0
        if "last_group" in st.session_state and st.session_state["last_group"] in groups:
            idx = groups.index(st.session_state["last_group"])
            
        selected_group = st.selectbox("Group", groups, index=idx, label_visibility="collapsed")
        st.session_state["last_group"] = selected_group

    with c5:
        st.markdown("###### 5. Region")
        area_list = sorted(utils.CITIES.keys())
        manual_area = st.selectbox(
            "Region", 
            area_list, 
            index=area_list.index(current_area),
            label_visibility="collapsed"
        )
        
        # Region Update Logic
        if manual_area != current_area:
            st.session_state["selected_price_area"] = manual_area
            city = utils.CITIES[manual_area]
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

    if start_d > end_d:
        st.error("⚠️ Start Date must be before End Date.")
        st.stop()

st.divider()

# ======================================================
# 3. LOAD DATA
# ======================================================
with st.spinner(f"Loading {selected_group} data..."):
    df = utils.load_map_stats(start_d, end_d, data_type, selected_group)
    geojson_areas = utils.load_geojson()
    geojson_munis = utils.load_municipality_geojson()

if not geojson_areas:
    st.error("Error: 'elspot_areas.geojson' not found.")
    st.stop()

if not df.empty:
    df["price_area_map"] = df["price_area"].astype(str).str.replace("NO", "NO ")

# ======================================================
# 4. MAP VISUALIZATION
# ======================================================
# Changed Ratio: [2.5, 1] makes map column narrower ("less broad")
c_map, c_info = st.columns([2.5, 1])

with c_map:
    # Overlay Toggle
    show_munis = st.toggle("🔍 Show Municipalities (Detailed Grid)", value=False)

    feature_key = "properties.ElSpotOmr"

    # --- LAYER 1: BASE MAP (Price Areas) ---
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
            center={"lat": 65.0, "lon": 16}, 
            opacity=0.6,
            labels={"avg_value": "MWh"}
        )
    else:
        # Empty Fallback
        fig = px.choropleth_mapbox(
            geojson=geojson_areas,
            locations=["NO 1", "NO 2", "NO 3", "NO 4", "NO 5"],
            featureidkey=feature_key,
            mapbox_style="carto-positron",
            zoom=4.2,
            center={"lat": 65.0, "lon": 16},
            opacity=0.3
        )

    # --- LAYER 2: MUNICIPALITIES (The "Grid") ---
    if show_munis and geojson_munis:
        first_props = geojson_munis['features'][0]['properties']
        muni_key = None
        
        # Robust ID detection
        if 'nummer' in first_props: muni_key = "properties.nummer"
        elif 'kommunenummer' in first_props: muni_key = "properties.kommunenummer"
        elif 'id' in first_props: muni_key = "properties.id"
        
        if muni_key:
            prop_id = muni_key.split('.')[1]
            muni_ids = [f['properties'].get(prop_id) for f in geojson_munis['features']]
            
            # --- FIX: NAME EXTRACTION LOGIC ---
            # Handles lists (e.g. [{"navn": "Oslo"}]) and plain strings
            hover_names = []
            for f in geojson_munis['features']:
                navn = f['properties'].get('navn')
                if isinstance(navn, list) and len(navn) > 0:
                    # Take the first name in the list
                    hover_names.append(navn[0].get('navn', 'Unknown'))
                elif isinstance(navn, str):
                    hover_names.append(navn)
                else:
                    hover_names.append('Unknown')

            fig.add_trace(go.Choroplethmapbox(
                geojson=geojson_munis,
                locations=muni_ids,
                featureidkey=muni_key,
                z=[1] * len(muni_ids),
                colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']], 
                marker_line_color='rgba(0, 0, 0, 0.6)', # Dark Grey
                marker_line_width=0.8, 
                showscale=False,
                hoverinfo='text',
                text=hover_names, # Use fixed names list
                name="Municipality"
            ))

    # --- LAYER 3: HIGHLIGHT ACTIVE REGION ---
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
        name="Active Region"
    ))

    # --- LAYER 4: PIN POINTER (Last Layer = Top Visibility) ---
    if "selected_coords" in st.session_state:
        coords = st.session_state["selected_coords"]
        fig.add_trace(go.Scattermapbox(
            lat=[coords['lat']],
            lon=[coords['lon']],
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=12,
                color='red',
                symbol='circle' # Simple clean circle
            ),
            text=["📍 Selected Point"],
            hoverinfo='text',
            name="Selected Point",
            showlegend=False
        ))

    # --- LAYOUT: LONG & NARROW ---
    fig.update_layout(
        margin=dict(r=0, t=0, l=0, b=0), 
        clickmode='event+select',
        height=800, # Increased Height
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )

    # --- RENDER & CAPTURE EVENTS ---
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

    if event and "selection" in event and event["selection"]["points"]:
        point = event["selection"]["points"][0]
        
        # 1. Update Pin Coordinates (ALWAYS WORKS)
        if "lat" in point:
            st.session_state["selected_coords"] = {"lat": point["lat"], "lon": point["lon"]}
            # Force rerun to show pin immediately
            st.rerun()
            
        # 2. Update Region (Only if not blocked by Municipality layer)
        if "location" in point:
            clicked = point["location"].replace(" ", "")
            # Check if clicked ID looks like a Price Area (NO1, etc.)
            if clicked in utils.CITIES and clicked != st.session_state["selected_price_area"]:
                st.session_state["selected_price_area"] = clicked
                city = utils.CITIES[clicked]
                st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
                st.rerun()

with c_info:
    # Details Panel
    st.info(f"""
    **Selection Details**
    
    🌍 **Region:** {st.session_state['selected_price_area']}
    
    📍 **Coordinates:**
    
    Lat: {st.session_state['selected_coords']['lat']:.4f}
    
    Lon: {st.session_state['selected_coords']['lon']:.4f}
    """)
    
    if show_munis:
        st.warning("ℹ️ **Note:** When Municipality Grid is ON, use the 'Region' dropdown to switch Price Areas.")
    
    st.markdown("#### 🛠️ Controls")
    st.caption("Use the map to click a location. Use the top bar to filter data.")