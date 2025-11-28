# Updated Streamlit map page with dual-coordinate support
# (default region center + clicked point) and region auto-selection with border highlight.

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import utils
from datetime import date
from shapely.geometry import shape, Point

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Map Selector", layout="wide")
utils.render_sidebar()

st.title("🇳🇴 Regional Energy Overview")

# ======================================================
# 1. INIT STATE
# ======================================================
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

# Store the default region coordinate separately
if "default_region_coords" not in st.session_state:
    default = utils.CITIES[st.session_state["selected_price_area"]]
    st.session_state["default_region_coords"] = {"lat": default["lat"], "lon": default["lon"]}

# Store clicked coordinate separately
if "clicked_coords" not in st.session_state:
    st.session_state["clicked_coords"] = None

current_area = st.session_state["selected_price_area"]

# ======================================================
# 2. CONTROLS
# ======================================================
with st.container():
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown("###### Source")
        data_type = st.radio("Source", ["Production", "Consumption"], horizontal=True, label_visibility="collapsed")

    with c2:
        st.markdown("###### Start Date")
        start_d = st.date_input("Start", date(2021, 1, 1), min_value=date(2021, 1, 1), max_value=date(2024, 12, 31), label_visibility="collapsed")

    with c3:
        st.markdown("###### End Date")
        end_d = st.date_input("End", date(2021, 12, 31), min_value=date(2021, 1, 1), max_value=date(2024, 12, 31), label_visibility="collapsed")

    with c4:
        st.markdown("###### Group")
        groups = ["hydro", "wind", "thermal", "solar", "other"] if data_type == "Production" else ["cabin", "household", "primary", "secondary", "tertiary"]
        selected_group = st.selectbox("Group", groups, index=0, label_visibility="collapsed")

    with c5:
        st.markdown("###### Region")
        area_list = sorted(utils.CITIES.keys())
        manual_area = st.selectbox("Region", area_list, index=area_list.index(st.session_state["selected_price_area"]), label_visibility="collapsed")

        if manual_area != st.session_state["selected_price_area"]:
            st.session_state["selected_price_area"] = manual_area
            city = utils.CITIES[manual_area]
            st.session_state["default_region_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

    if start_d > end_d: st.error("Start Date must be before End Date."); st.stop()

st.divider()

# ======================================================
# 3. DATA & GEOMETRY
# ======================================================
with st.spinner("Loading Map Data..."):
    df = utils.load_map_stats(start_d, end_d, data_type, selected_group)
    geojson_areas = utils.load_geojson()
    geojson_munis = utils.load_municipality_geojson()

if not geojson_areas:
    st.error("Error: 'elspot_areas.geojson' not found.")
    st.stop()

if not df.empty:
    df["price_area_map"] = df["price_area"].astype(str).str.replace("NO", "NO ")

@st.cache_data
def generate_click_mesh():
    lats = np.arange(57.5, 71.5, 0.2)
    lons = np.arange(4.0, 31.5, 0.3)
    mesh_lats, mesh_lons = np.meshgrid(lats, lons)
    return pd.DataFrame({"lat": mesh_lats.flatten(), "lon": mesh_lons.flatten()})

def get_region_from_click(lat, lon, geo_data):
    point = Point(lon, lat)
    for f in geo_data['features']:
        try:
            if shape(f['geometry']).contains(point):
                return f['properties'].get('ElSpotOmr') or f['properties'].get('ElSpot_omr')
        except:
            continue
    return None

# Mesh
mesh_df = generate_click_mesh()

# ======================================================
# 4. MAP VISUALIZATION
# ======================================================
c_map, c_info = st.columns([3, 1])

with c_map:
    show_munis = st.toggle("🔍 View Municipalities", value=False)
    feature_key = "properties.ElSpotOmr"

    # Base layer
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
            center={"lat": 65.0, "lon": 16.0},
            opacity=0.6,
            labels={"avg_value": "MWh", "price_area_map": "Region"},
            hover_name="price_area_map",
            hover_data={"price_area_map": False, "avg_value": ":.2f"},
        )
    else:
        fig = px.choropleth_mapbox(
            geojson=geojson_areas,
            locations=["NO 1"],
            featureidkey=feature_key,
            mapbox_style="carto-positron",
            zoom=4.5,
            center={"lat": 65.0, "lon": 16.0},
            opacity=0.3,
        )

    # Municipalities
    if show_munis and geojson_munis:
        fk = geojson_munis['features'][0]['properties']
        muni_key = "properties.nummer" if 'nummer' in fk else ("properties.kommunenummer" if 'kommunenummer' in fk else "properties.id")
        prop = muni_key.split('.')[1]
        locs = [f['properties'].get(prop) for f in geojson_munis['features']]
        names = []
        for f in geojson_munis['features']:
            navn = f['properties'].get('navn')
            if isinstance(navn, list) and len(navn) > 0:
                names.append(navn[0].get('navn', 'Unknown'))
            elif isinstance(navn, str):
                names.append(navn)
            else:
                names.append('Unknown')

        fig.add_trace(go.Choroplethmapbox(
            geojson=geojson_munis,
            locations=locs,
            featureidkey=muni_key,
            z=[1] * len(locs),
            colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']],
            marker_line_color='rgba(20,20,20,0.8)',
            marker_line_width=0.8,
            showscale=False,
            hoverinfo='text',
            text=names,
            name="Municipalities",
        ))

    # Mesh for clicks
    fig.add_trace(go.Scattermapbox(
        lat=mesh_df["lat"],
        lon=mesh_df["lon"],
        mode='markers',
        marker=go.scattermapbox.Marker(size=25, color='white', opacity=0),
        hoverinfo='skip',
        name="Click Mesh"
    ))

    # Highlight Border of selected region
    hl = st.session_state["selected_price_area"].replace("NO", "NO ")
    fig.add_trace(go.Choroplethmapbox(
        geojson=geojson_areas,
        locations=[hl],
        featureidkey=feature_key,
        z=[1],
        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
        marker_line_color="red",
        marker_line_width=4,
        showscale=False,
        hoverinfo="skip",
        name="Selected Border",
    ))

    # Default region pin (blue)
    dr = st.session_state["default_region_coords"]
    fig.add_trace(go.Scattermapbox(
        lat=[dr['lat']],
        lon=[dr['lon']],
        mode='markers',
        marker=go.scattermapbox.Marker(size=14, color='blue', symbol='circle'),
        text=["Default Region Center"],
        hoverinfo='text',
        name="Region Center",
    ))

    # Clicked point pin (red)
    if st.session_state.get("clicked_coords"):
        cc = st.session_state["clicked_coords"]
        fig.add_trace(go.Scattermapbox(
            lat=[cc['lat']],
            lon=[cc['lon']],
            mode='markers',
            marker=go.scattermapbox.Marker(size=14, color='red', symbol='circle'),
            text=["Clicked Point"],
            hoverinfo='text',
            name="Clicked Point",
        ))

    fig.update_layout(margin=dict(r=0, t=0, l=0, b=0), clickmode='event+select', height=800)

    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

    # --- EVENT HANDLING ---
    if event and "selection" in event and event["selection"]["points"]:
        p = event["selection"]["points"][0]

        if "lat" in p:
            lat = p["lat"]
            lon = p["lon"]

            # Save clicked point
            st.session_state["clicked_coords"] = {"lat": lat, "lon": lon}

            # Determine region
            rid = get_region_from_click(lat, lon, geojson_areas)
            if rid:
                clean = rid.replace(" ", "")
                if clean in utils.CITIES:
                    st.session_state["selected_price_area"] = clean

            st.rerun()

with c_info:
    st.markdown("#### 📌 Selection Status")
    with st.container(border=True):

        st.info(f"**Active Region**\n# {st.session_state['selected_price_area']}")

        st.divider()

        st.markdown("### 🟦 Default Region Center")
        d = st.session_state["default_region_coords"]
        st.write(f"Lat: {d['lat']:.4f}")
        st.write(f"Lon: {d['lon']:.4f}")

        st.divider()

        st.markdown("### 🔴 Clicked Point")
        if st.session_state.get("clicked_coords"):
            c = st.session_state["clicked_coords"]
            st.write(f"Lat: {c['lat']:.4f}")
            st.write(f"Lon: {c['lon']:.4f}")
        else:
            st.caption("Click on the map to set a point.")
