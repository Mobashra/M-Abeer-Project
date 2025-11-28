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
    st.session_state["selected_coords"] = {"lat": 59.91, "lon": 10.75}

current_area = st.session_state["selected_price_area"]

# ======================================================
# 2. CONTROLS (5 Columns Dashboard)
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
        end_d = st.date_input("End", date(2023, 12, 31), min_value=date(2021, 1, 1), max_value=date(2024, 12, 31), label_visibility="collapsed")

    with c4:
        st.markdown("###### 4. Group")
        groups = ["hydro", "wind", "thermal", "solar", "other"] if data_type == "Production" else ["household", "industry", "primary", "tertiary"]
        idx = 0
        if "last_group" in st.session_state and st.session_state["last_group"] in groups:
            idx = groups.index(st.session_state["last_group"])
        selected_group = st.selectbox("Group", groups, index=idx, label_visibility="collapsed")
        st.session_state["last_group"] = selected_group

    with c5:
        st.markdown("###### 5. Region")
        area_list = sorted(utils.CITIES.keys())
        manual_area = st.selectbox("Region", area_list, index=area_list.index(current_area), label_visibility="collapsed")
        
        if manual_area != current_area:
            st.session_state["selected_price_area"] = manual_area
            city = utils.CITIES[manual_area]
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

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
# 4. MAP VISUALIZATION (Plotly)
# ======================================================
c_map, c_info = st.columns([3, 1])

with c_map:
    # Bonus Toggle
    show_munis = st.toggle("🔍 Show Municipalities (Bonus)", value=False)

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
            center={"lat": 65.0, "lon": 16.0}, 
            opacity=0.6,
            labels={"avg_value": "MWh"}
        )
    else:
        fig = px.choropleth_mapbox(
            geojson=geojson_areas,
            locations=["NO 1", "NO 2", "NO 3", "NO 4", "NO 5"],
            featureidkey=feature_key,
            mapbox_style="carto-positron",
            zoom=4.2,
            center={"lat": 65.0, "lon": 16.0},
            opacity=0.3
        )

    # --- LAYER 2: MUNICIPALITIES (Overlay) ---
    if show_munis and geojson_munis:
        # Detect correct Key
        first = geojson_munis['features'][0]['properties']
        muni_key = None
        if 'nummer' in first: muni_key = "properties.nummer"
        elif 'kommunenummer' in first: muni_key = "properties.kommunenummer"
        elif 'id' in first: muni_key = "properties.id"
        
        if muni_key:
            # Extract IDs for location mapping
            key_name = muni_key.split('.')[1]
            locs = [f['properties'].get(key_name) for f in geojson_munis['features']]
            
            fig.add_trace(go.Choroplethmapbox(
                geojson=geojson_munis,
                locations=locs,
                featureidkey=muni_key,
                z=[1] * len(locs), # Dummy value
                colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']], # Transparent fill
                marker_line_color='rgba(30, 30, 30, 0.8)', # Dark Grey Lines
                marker_line_width=1.0, 
                showscale=False,
                hoverinfo='skip', # Allow clicking through to Price Area
                name="Municipalities"
            ))

    # --- LAYER 3: HIGHLIGHT SELECTED REGION ---
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
        name="Active Region"
    ))

    # --- LAYER 4: CLICK POINTER (The Pin) ---
    if "selected_coords" in st.session_state:
        coords = st.session_state["selected_coords"]
        fig.add_trace(go.Scattermapbox(
            lat=[coords['lat']],
            lon=[coords['lon']],
            mode='markers+text',
            marker=go.scattermapbox.Marker(size=14, color='red', symbol='circle'),
            text=["📍"], # Visual Pin
            textposition="top center",
            hoverinfo='text',
            hovertext=f"Selected: {st.session_state['selected_price_area']}",
            name="Pointer"
        ))

    # Layout: Taller and Narrower
    fig.update_layout(
        margin=dict(r=0, t=0, l=0, b=0), 
        clickmode='event+select',
        height=750, 
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )

    # --- RENDER MAP ---
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

    # --- INTERACTION LOGIC ---
    if event and "selection" in event and event["selection"]["points"]:
        point = event["selection"]["points"][0]
        
        # 1. Capture Lat/Lon (Always updates Pin)
        if "lat" in point:
            st.session_state["selected_coords"] = {"lat": point["lat"], "lon": point["lon"]}
            
        # 2. Capture Region (Only if clicking a valid Price Area)
        if "location" in point:
            clicked = point["location"].replace(" ", "")
            if clicked in utils.CITIES and clicked != st.session_state["selected_price_area"]:
                st.session_state["selected_price_area"] = clicked
                city = utils.CITIES[clicked]
                st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
                st.rerun()
        else:
            # If we clicked empty space (or Municipality layer with skip), just show pin
            st.rerun()

with c_info:
    st.info(f"""
    **Selection Details**
    
    🌍 **Region:** {st.session_state['selected_price_area']}
    
    📍 **Coordinates:**
    {st.session_state['selected_coords']['lat']:.4f}, {st.session_state['selected_coords']['lon']:.4f}
    """)
    
    st.markdown("#### 💡 Guide")
    st.caption("""
    1. **Filter Data** using the top dashboard.
    2. **Click Map** to select a specific location (Red Pin).
    3. **Toggle Municipalities** to see local borders.
    """)