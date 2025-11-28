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
    # Default to Oslo coordinates
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

current_area = st.session_state["selected_price_area"]

# ======================================================
# 2. TOP CONTROL BAR
# ======================================================
with st.container():
    c1, c2, c3, c4 = st.columns([1.2, 2.0, 1.2, 1.2])

    with c1:
        st.markdown("###### 1. Data Source")
        data_type = st.radio(
            "Source", 
            ["Production", "Consumption"], 
            horizontal=True, 
            label_visibility="collapsed"
        )

    with c2:
        st.markdown("###### 2. Time Period (2021-2024)")
        d1, d2 = st.columns(2)
        with d1:
            start_d = st.date_input(
                "Start",
                value=date(2021, 1, 1),
                min_value=date(2021, 1, 1),
                max_value=date(2024, 12, 31),
                format="DD.MM.YYYY"
            )
        with d2:
            end_d = st.date_input(
                "End",
                value=date(2021, 12, 31),
                min_value=date(2021, 1, 1),
                max_value=date(2024, 12, 31),
                format="DD.MM.YYYY"
            )
        
        if start_d > end_d:
            st.error("Start Date must be before End Date.")
            st.stop()

    with c3:
        st.markdown(f"###### 3. {data_type} Group")
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

    with c4:
        st.markdown("###### 4. Region (Fallback)")
        area_list = sorted(utils.CITIES.keys())
        manual_area = st.selectbox(
            "Select Area", 
            area_list, 
            index=area_list.index(current_area),
            label_visibility="collapsed"
        )
        
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
# 4. MAP VISUALIZATION
# ======================================================
c_map, c_info = st.columns([3, 1])

with c_map:
    # Toggle for Detailed View
    show_munis = st.toggle("🔍 Show Municipalities (Detailed Grid)", value=False)

    feature_key = "properties.ElSpotOmr"

    # --- LAYER 1: PRICE AREAS (Base) ---
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
            center={"lat": 65.0, "lon": 16}, 
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
            center={"lat": 65.0, "lon": 16},
            opacity=0.3
        )

    # --- LAYER 2: MUNICIPALITIES (Overlay) ---
    if show_munis and geojson_munis:
        # Detect correct ID Key
        first_props = geojson_munis['features'][0]['properties']
        muni_key = None
        if 'nummer' in first_props: muni_key = "properties.nummer"
        elif 'kommunenummer' in first_props: muni_key = "properties.kommunenummer"
        elif 'id' in first_props: muni_key = "properties.id"
        
        if muni_key:
            prop_id = muni_key.split('.')[1]
            muni_ids = [f['properties'].get(prop_id) for f in geojson_munis['features']]
            
            # EXTRACT NAMES FOR HOVER
            # Use 'navn' (list of dicts) or just 'navn' string
            hover_names = []
            for f in geojson_munis['features']:
                name_prop = f['properties'].get('navn')
                if isinstance(name_prop, list) and len(name_prop) > 0:
                    hover_names.append(name_prop[0].get('navn', 'Unknown'))
                elif isinstance(name_prop, str):
                    hover_names.append(name_prop)
                else:
                    hover_names.append('Unknown Municipality')

            fig.add_trace(go.Choroplethmapbox(
                geojson=geojson_munis,
                locations=muni_ids,
                featureidkey=muni_key,
                z=[1] * len(muni_ids),
                colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']], 
                marker_line_color='rgba(20, 20, 20, 0.8)', 
                marker_line_width=1.0, 
                showscale=False,
                hoverinfo='text',
                text=hover_names, # <--- THIS ENABLES HOVER NAMES
                name="Municipalities"
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

    # --- LAYER 4: CLICK POINTER (Pin) ---
    # This draws a marker where the user clicked
    if "selected_coords" in st.session_state:
        coords = st.session_state["selected_coords"]
        fig.add_trace(go.Scattermapbox(
            lat=[coords['lat']],
            lon=[coords['lon']],
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=14,
                color='red',
                symbol='marker'
            ),
            text=["Selected Location"],
            hoverinfo='text',
            name="Selected Point"
        ))

    # Layout Setup
    fig.update_layout(
        margin=dict(r=0, t=0, l=0, b=0), 
        clickmode='event+select',
        height=650, 
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )

    # Render Map
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

    # --- HANDLE CLICKS ---
    if event and "selection" in event and event["selection"]["points"]:
        point = event["selection"]["points"][0]
        
        # 1. Capture Coordinates (Always)
        if "lat" in point:
            st.session_state["selected_coords"] = {"lat": point["lat"], "lon": point["lon"]}
            
        # 2. Capture Region (Only if clicking price area, not muni layer)
        # We check if the click location looks like "NO 1"
        if "location" in point:
            clicked = point["location"].replace(" ", "")
            if clicked in utils.CITIES and clicked != st.session_state["selected_price_area"]:
                st.session_state["selected_price_area"] = clicked
                # We do NOT update coords here to center of city, 
                # effectively respecting the user's specific click point.
                st.rerun()
        else:
            # If we just clicked a coordinate (lat/lon) but no location ID (e.g. ocean or muni)
            # just rerun to show the pin
            st.rerun()

with c_info:
    st.info(f"""
    **Current Selection**
    
    ### {st.session_state['selected_price_area']}
    
    **Pin Coordinates:**
    
    Lat: {st.session_state['selected_coords']['lat']:.4f}
    
    Lon: {st.session_state['selected_coords']['lon']:.4f}
    """)
    
    st.markdown("#### 💡 Tips")
    st.caption("""
    1. **Hover** over a municipality to see its name.
    2. **Click** anywhere to drop a pin for weather analysis.
    3. **Switch Data** using the top-left radio buttons.
    """)