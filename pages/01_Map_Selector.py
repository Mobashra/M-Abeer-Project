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

st.title("Map and Price Area Selector")
st.markdown("Click on the map to select a location and its Price Area.")

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
        st.markdown("###### Energy Group")
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
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

    if start_d > end_d: st.error("Start Date must be before End Date."); st.stop()

st.divider()

# ======================================================
# 3. LOAD DATA & HELPERS
# ======================================================
with st.spinner("Loading Map Data..."):
    df = utils.load_map_stats(start_d, end_d, data_type, selected_group)
    geojson_areas = utils.load_geojson()
    geojson_munis = utils.load_municipality_geojson()

if not geojson_areas: st.error("Error: 'elspot_areas.geojson' not found."); st.stop()

# --- FIX 1: SANITIZE PRICE AREA NAMES ---
# This ensures that "NO1" in data matches "NO 1" in GeoJSON
if geojson_areas:
    for f in geojson_areas['features']:
        p = f['properties']
        # Find the name (it could be ElSpotOmr, navn, etc.)
        raw_name = p.get('ElSpotOmr') or p.get('navn') or p.get('name') or p.get('omrnavn') or "Unknown"
        # Standardize to "NO 1" format
        clean_name = str(raw_name).replace("NO", "NO ").replace("  ", " ").strip()
        f['properties']['std_name'] = clean_name
        f['id'] = clean_name # Vital for Plotly linkage

# --- FIX 2: PREPARE DATAFRAME ---
if not df.empty: 
    # Match the DataFrame format to the GeoJSON format "NO 1"
    df["price_area_map"] = df["price_area"].astype(str).str.replace("NO", "NO ").str.replace("  ", " ").str.strip()

def get_clicked_area_id(lat, lon, geo_data):
    """Robust Hit-Testing for Price Areas."""
    if not geo_data: return None
    point = Point(lon, lat)
    for f in geo_data['features']:
        try:
            if shape(f['geometry']).contains(point):
                return f['properties'].get('std_name')
        except: continue
    return None

# --- CREATE CLICKABLE GRID ---
clickable_points = []
if geojson_munis:
    for f in geojson_munis['features']:
        try:
            geom = shape(f['geometry'])
            cent = geom.centroid
            props = f['properties']
            
            # Smart Name Logic
            name = "Unknown"
            if 'kommunenavn' in props: name = props['kommunenavn']
            elif 'navn' in props:
                val = props['navn']
                if isinstance(val, list) and len(val) > 0: name = val[0].get('navn', str(val[0])) if isinstance(val[0], dict) else str(val[0])
                else: name = str(val)
            elif 'name' in props: name = props['name']
            
            clickable_points.append({"lat": cent.y, "lon": cent.x, "name": name})
        except: continue

df_clicks = pd.DataFrame(clickable_points)

# ======================================================
# 4. MAP VISUALIZATION
# ======================================================
# ======================================================
# 4. MAP VISUALIZATION
# ======================================================
c_map, c_info = st.columns([3, 1])

with c_map:
    show_munis = st.toggle("🔍 View Municipalities", value=False)
    feature_key = "properties.std_name"

    # --- LAYER 1: PRICE AREAS (Background Shapes) ---
    if not df.empty:
        fig = px.choropleth_mapbox(
            df, geojson=geojson_areas, locations="price_area_map", featureidkey=feature_key,
            color="avg_value", color_continuous_scale="Viridis",
            mapbox_style="carto-positron", zoom=4.5, center={"lat": 65.0, "lon": 16.0},
            opacity=0.6,
            labels={"avg_value": "MWh", "price_area_map": "Region"},
            hover_name="price_area_map"
        )
    else:
        fig = px.choropleth_mapbox(
            geojson=geojson_areas, locations=["NO 1"], featureidkey=feature_key,
            mapbox_style="carto-positron", zoom=4.5, center={"lat": 65.0, "lon": 16.0}, opacity=0.3
        )

    # --- LAYER 2: MUNICIPALITIES (Optional Outline) ---
    if show_munis and geojson_munis:
        # 1. Find the ID key
        first = geojson_munis['features'][0]['properties']
        muni_key = "properties.nummer" if 'nummer' in first else ("properties.kommunenummer" if 'kommunenummer' in first else "properties.id")
        
        if muni_key:
            prop = muni_key.split('.')[1]
            locs = []
            for f in geojson_munis['features']:
                locs.append(f['properties'].get(prop))

            fig.add_trace(go.Choroplethmapbox(
                geojson=geojson_munis, 
                locations=locs, 
                featureidkey=muni_key, 
                z=[1]*len(locs),
                colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']], 
                marker_line_color='rgba(50, 50, 50, 0.5)', 
                marker_line_width=0.5,
                showscale=False, 
                hoverinfo='skip', 
                name="Municipalities"
            ))

    # --- LAYER 3: CLICK GRID (The "Touch Screen" Layer) ---
    if not df_clicks.empty:
        fig.add_trace(go.Scattermapbox(
            lat=df_clicks["lat"], lon=df_clicks["lon"],
            mode='markers', 
            marker=go.scattermapbox.Marker(size=45, color='white', opacity=0.01), 
            hoverinfo='text', 
            text=df_clicks["name"],
            name="Region",
            showlegend=False  # <--- ADD THIS: Hides "Region" from the legend box
        ))

    # --- LAYER 4: HIGHLIGHT SELECTED AREA ---
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
            text=["📍 Pin"], hoverinfo='text', name="Pin"
        ))

    # --- LAYER 6: STATIC TEXT LABELS (Moved to END to be ON TOP) ---
    lbl_lats = []
    lbl_lons = []
    lbl_names = []
    
    for area_name, coords in utils.CITIES.items():
        # Space out labels slightly if needed, or use exact city center
        lbl_names.append(area_name)
        lbl_lats.append(coords['lat'])
        lbl_lons.append(coords['lon'])

    fig.add_trace(go.Scattermapbox(
        lat=lbl_lats,
        lon=lbl_lons,
        mode='text',
        text=lbl_names,
        textfont=dict(size=20, color='black', family="Arial Black"), 
        hoverinfo='skip', # Don't interfere with clicks
        showlegend=False
    ))

    fig.update_layout(margin=dict(r=0, t=0, l=0, b=0), clickmode='event+select', height=800)
    
    # RENDER MAP
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

    # --- INTERACTION LOGIC ---
    if event and "selection" in event and event["selection"]["points"]:
        point = event["selection"]["points"][0]
        
        # SCENARIO A: Exact Click (User hit the invisible dot)
        if "lat" in point:
            clat, clon = point["lat"], point["lon"]
            st.session_state["selected_coords"] = {"lat": clat, "lon": clon}
            
            # Update Region
            hit_id = get_clicked_area_id(clat, clon, geojson_areas)
            if hit_id:
                clean = hit_id.replace(" ", "")
                if clean in utils.CITIES:
                    st.session_state["selected_price_area"] = clean
            
            # Fetch Elevation
            elev = utils.fetch_elevation(clat, clon)
            if elev is not None: st.session_state["elevation"] = elev
            
            st.rerun()

        # SCENARIO B: Shape Click (Fallback)
        elif "location" in point:
            clicked_clean = point["location"].replace(" ", "")
            
            if clicked_clean in utils.CITIES:
                st.session_state["selected_price_area"] = clicked_clean
                
                # FORCE PIN UPDATE to Region Center
                center = utils.CITIES[clicked_clean]
                st.session_state["selected_coords"] = {"lat": center["lat"], "lon": center["lon"]}
                
                elev = utils.fetch_elevation(center["lat"], center["lon"])
                if elev is not None: st.session_state["elevation"] = elev

                st.rerun()


            

with c_info:
    st.markdown("#### Selection Status")
    with st.container(border=True):
        # 1. REGION INFO (Blue)
        curr = st.session_state["selected_price_area"]
        center = utils.CITIES[curr]
        st.info(f"**Active Region**\n# {curr}")
        st.caption("**Region Center:**")
        st.write(f"Latitude: {center['lat']:.4f}\n\nLongitude: {center['lon']:.4f}")
        
    
        
        st.divider()
        
        # 2. PIN INFO (Red)
        if "selected_coords" in st.session_state:
            pin = st.session_state["selected_coords"]
            st.error("**📍 Pin Location**")
            st.write(f"Lat: {pin['lat']:.4f}\nLon: {pin['lon']:.4f}")
        
        # 3. ELEVATION (Orange - Custom Style)
        if "elevation" in st.session_state:
            elev = st.session_state["elevation"]
            st.warning("**⛰️ Elevation**")
            st.write(f"{elev:.1f} meters above sea level")
        else:
            st.caption("Click map to fetch elevation.")