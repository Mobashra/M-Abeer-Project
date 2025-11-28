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
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

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
            # Manual override: Reset to center
            city = utils.CITIES[manual_area]
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

    if start_d > end_d: st.error("Start Date must be before End Date."); st.stop()

st.divider()

# ======================================================
# 3. DATA & GEOMETRY ENGINE
# ======================================================
with st.spinner("Loading Map Data..."):
    df = utils.load_map_stats(start_d, end_d, data_type, selected_group)
    geojson_areas = utils.load_geojson()
    geojson_munis = utils.load_municipality_geojson()

if not geojson_areas: st.error("Error: 'elspot_areas.geojson' not found."); st.stop()
if not df.empty: df["price_area_map"] = df["price_area"].astype(str).str.replace("NO", "NO ")

@st.cache_data
def generate_click_mesh():
    """
    Generates a dense grid of invisible points covering Norway.
    This allows Plotly to register clicks *anywhere* and return coordinates.
    """
    # Norway Bounding Box (Approx)
    lats = np.arange(57.5, 71.5, 0.2) # 0.2 degree steps (~20km)
    lons = np.arange(4.0, 31.5, 0.3)
    
    mesh_lats, mesh_lons = np.meshgrid(lats, lons)
    return pd.DataFrame({"lat": mesh_lats.flatten(), "lon": mesh_lons.flatten()})

def get_region_from_click(lat, lon, geo_data):
    """Finds which Price Area polygon contains the coordinate."""
    if not geo_data: return None
    point = Point(lon, lat)
    for f in geo_data['features']:
        try:
            if shape(f['geometry']).contains(point):
                # Return ID like "NO 1"
                return f['properties'].get('ElSpotOmr') or f['properties'].get('ElSpot_omr')
        except: continue
    return None

# Generate the active mesh
df_mesh = generate_click_mesh()

# ======================================================
# 4. MAP VISUALIZATION
# ======================================================
c_map, c_info = st.columns([3, 1])

with c_map:
    show_munis = st.toggle("🔍 View Municipalities", value=False)
    feature_key = "properties.ElSpotOmr"

    # --- LAYER 1: PRICE AREAS (Base) ---
    if not df.empty:
        fig = px.choropleth_mapbox(
            df, geojson=geojson_areas, locations="price_area_map", featureidkey=feature_key,
            color="avg_value", color_continuous_scale="Viridis",
            mapbox_style="carto-positron", zoom=4.5, center={"lat": 65.0, "lon": 16.0},
            opacity=0.6, 
            labels={"avg_value": "MWh", "price_area_map": "Region"},
            hover_name="price_area_map",
            hover_data={"price_area_map": False, "avg_value": ":.2f"}
        )
    else:
        fig = px.choropleth_mapbox(
            geojson=geojson_areas, locations=["NO 1"], featureidkey=feature_key,
            mapbox_style="carto-positron", zoom=4.5, center={"lat": 65.0, "lon": 16.0}, opacity=0.3
        )

    # --- LAYER 2: MUNICIPALITIES ---
    if show_munis and geojson_munis:
        first = geojson_munis['features'][0]['properties']
        muni_key = "properties.nummer" if 'nummer' in first else ("properties.kommunenummer" if 'kommunenummer' in first else "properties.id")
        if muni_key:
            prop = muni_key.split('.')[1]
            locs = [f['properties'].get(prop) for f in geojson_munis['features']]
            names = []
            for f in geojson_munis['features']:
                navn = f['properties'].get('navn')
                if isinstance(navn, list) and len(navn) > 0: names.append(navn[0].get('navn', 'Unknown'))
                elif isinstance(navn, str): names.append(navn)
                else: names.append('Unknown')

            fig.add_trace(go.Choroplethmapbox(
                geojson=geojson_munis, locations=locs, featureidkey=muni_key, z=[1]*len(locs),
                colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']],
                marker_line_color='rgba(20, 20, 20, 0.8)', marker_line_width=0.8,
                showscale=False, hoverinfo='text', text=names, name="Municipalities"
            ))

    # --- LAYER 3: ACTIVE MESH (The Click Fix) ---
    # Large transparent markers cover the map to capture clicks everywhere
    fig.add_trace(go.Scattermapbox(
        lat=df_mesh["lat"], lon=df_mesh["lon"],
        mode='markers',
        marker=go.scattermapbox.Marker(size=25, color='white', opacity=0), 
        hoverinfo='skip', name="Click Mesh"
    ))

    # --- LAYER 4: HIGHLIGHT BORDER ---
    hl_name = st.session_state["selected_price_area"].replace("NO", "NO ")
    fig.add_trace(go.Choroplethmapbox(
        geojson=geojson_areas, locations=[hl_name], featureidkey=feature_key, z=[1],
        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
        marker_line_color="red", marker_line_width=4, showscale=False, hoverinfo="skip",
        name="Selected"
    ))

    # --- LAYER 5: RED PIN ---
    if "selected_coords" in st.session_state:
        coords = st.session_state["selected_coords"]
        fig.add_trace(go.Scattermapbox(
            lat=[coords['lat']], lon=[coords['lon']],
            mode='markers', marker=go.scattermapbox.Marker(size=14, color='red', symbol='circle'),
            text=["📍 Selected"], hoverinfo='text', name="Pin"
        ))

    fig.update_layout(margin=dict(r=0, t=0, l=0, b=0), clickmode='event+select', height=800, legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

    # --- INTERACTION HANDLER ---
    if event and "selection" in event and event["selection"]["points"]:
        point = event["selection"]["points"][0]
        
        # 1. CHECK FOR COORDINATES (From Mesh or Pin)
        if "lat" in point:
            click_lat = point["lat"]
            click_lon = point["lon"]
            
            # Update Pin
            st.session_state["selected_coords"] = {"lat": click_lat, "lon": click_lon}
            
            # Update Elevation
            elev = utils.fetch_elevation(click_lat, click_lon)
            if elev is not None: st.session_state["elevation"] = elev

            # Update Region (Hit Test)
            hit_id = get_region_from_click(click_lat, click_lon, geojson_areas)
            if hit_id:
                # Normalize "NO 1" -> "NO1"
                clean_id = hit_id.replace(" ", "")
                if clean_id in utils.CITIES and clean_id != st.session_state["selected_price_area"]:
                    st.session_state["selected_price_area"] = clean_id
            
            st.rerun()
        
        # 2. FALLBACK (If they somehow clicked a polygon directly)
        elif "location" in point:
            clicked = point["location"].replace(" ", "")
            if clicked in utils.CITIES and clicked != st.session_state["selected_price_area"]:
                st.session_state["selected_price_area"] = clicked
                st.rerun()

with c_info:
    st.markdown("#### 📌 Selection Status")
    with st.container(border=True):
        # Region Info
        curr = st.session_state["selected_price_area"]
        st.info(f"**Active Region**\n# {curr}")
        
        st.divider()
        
        # Pin Info
        pin = st.session_state["selected_coords"]
        st.error(f"**📍 Pin Location**\n\nLat: {pin['lat']:.4f}\nLon: {pin['lon']:.4f}")
        
        # Elevation
        if "elevation" in st.session_state:
            st.metric("⛰️ Elevation", f"{st.session_state['elevation']} m")
        else:
            st.caption("Click map to fetch elevation.")