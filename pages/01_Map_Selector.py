import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import utils
from datetime import date
import json
from shapely.geometry import shape, Point

st.set_page_config(page_title="Map Selector", layout="wide")

# --- 1. SETUP ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
if "selected_coords" not in st.session_state:
    st.session_state["selected_coords"] = {"lat": 59.91, "lon": 10.75}

utils.render_sidebar()

st.title("🗺️ Regional Map Selector")

# --- 2. CONTROLS (5-Column Layout) ---
with st.container():
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        data_type = st.radio("Source", ["Production", "Consumption"], horizontal=True, label_visibility="collapsed")
    with c2:
        start_d = st.date_input("Start", date(2021, 1, 1), min_value=date(2021, 1, 1), max_value=date(2024, 12, 31), label_visibility="collapsed")
    with c3:
        end_d = st.date_input("End", date(2023, 12, 31), min_value=date(2021, 1, 1), max_value=date(2024, 12, 31), label_visibility="collapsed")
    with c4:
        groups = ["hydro", "wind", "thermal", "solar", "other"] if data_type == "Production" else ["household", "industry", "primary", "tertiary"]
        selected_group = st.selectbox("Group", groups, label_visibility="collapsed")
    with c5:
        # Fallback Selector
        areas = sorted(utils.CITIES.keys())
        manual_area = st.selectbox("Region", areas, index=areas.index(st.session_state["selected_price_area"]), label_visibility="collapsed")
        if manual_area != st.session_state["selected_price_area"]:
            st.session_state["selected_price_area"] = manual_area
            city = utils.CITIES[manual_area]
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

st.divider()

# --- 3. HELPER: HIT TESTING ---
@st.cache_data
def get_geo_data():
    return utils.load_geojson(), utils.load_municipality_geojson()

def get_clicked_area(lat, lon, geo_data):
    """Finds which Price Area polygon contains the click."""
    if not geo_data: return None
    point = Point(lon, lat)
    for f in geo_data['features']:
        try:
            if shape(f['geometry']).contains(point):
                return f['properties'].get('ElSpotOmr') or f['properties'].get('ElSpot_omr')
        except: continue
    return None

# --- 4. MAP LOGIC ---
c_map, c_info = st.columns([2.5, 1])

with c_map:
    # Bonus Toggle
    show_munis = st.toggle("🔍 Show Municipalities (Bonus Overlay)", value=False)

    with st.spinner("Rendering Map..."):
        df = utils.load_map_stats(start_d, end_d, data_type, selected_group)
        geo_areas, geo_munis = get_geo_data()
        
        feature_key = "properties.ElSpotOmr"
        
        # --- LAYER 1: PRICE AREAS ---
        if not df.empty:
            df["price_area_map"] = df["price_area"].astype(str).str.replace("NO", "NO ")
            fig = px.choropleth_mapbox(
                df, geojson=geo_areas, locations="price_area_map", featureidkey=feature_key,
                color="avg_value", color_continuous_scale="Viridis",
                mapbox_style="carto-positron", zoom=4.2, center={"lat": 65.0, "lon": 16},
                opacity=0.6, labels={"avg_value": "MWh"}
            )
        else:
            fig = px.choropleth_mapbox(
                geojson=geo_areas, locations=["NO 1"], featureidkey=feature_key,
                mapbox_style="carto-positron", zoom=4.2, center={"lat": 65.0, "lon": 16}, opacity=0.3
            )

        # --- LAYER 2: MUNICIPALITIES (BONUS) ---
        if show_munis and geo_munis:
            # Auto-detect key
            first = geo_munis['features'][0]['properties']
            m_key = "properties.nummer" if 'nummer' in first else ("properties.kommunenummer" if 'kommunenummer' in first else "properties.id")
            
            if m_key:
                m_prop = m_key.split('.')[1]
                locs = [f['properties'].get(m_prop) for f in geo_munis['features']]
                # HIGH VISIBILITY: Black lines, transparent fill
                fig.add_trace(go.Choroplethmapbox(
                    geojson=geo_munis, locations=locs, featureidkey=m_key, z=[1]*len(locs),
                    colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']],
                    marker_line_color='rgba(0, 0, 0, 0.8)', marker_line_width=1.0,
                    showscale=False, hoverinfo='text',
                    text=[f['properties'].get('navn', [{}])[0].get('navn', 'Muni') if isinstance(f['properties'].get('navn'), list) else 'Muni' for f in geo_munis['features']],
                    name="Municipalities"
                ))

        # --- LAYER 3: HIGHLIGHT ---
        hl_name = st.session_state["selected_price_area"].replace("NO", "NO ")
        fig.add_trace(go.Choroplethmapbox(
            geojson=geo_areas, locations=[hl_name], featureidkey=feature_key, z=[1],
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            marker_line_color="red", marker_line_width=3, showscale=False, hoverinfo="skip"
        ))

        # --- LAYER 4: POINTER (Hidden but Active) ---
        # We draw a Scatter trace so Plotly registers clicks, but make it transparent/small
        # if you really want "no pointer visible". 
        # BUT good UX requires feedback. I will make a tiny red dot.
        if st.session_state["selected_coords"]:
            coords = st.session_state["selected_coords"]
            fig.add_trace(go.Scattermapbox(
                lat=[coords['lat']], lon=[coords['lon']],
                mode='markers', marker=go.scattermapbox.Marker(size=8, color='red'),
                hoverinfo='text', text="Selected Point", showlegend=False
            ))

        fig.update_layout(margin=dict(r=0, t=0, l=0, b=0), clickmode='event+select', height=800)
        
        # --- RENDER ---
        event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

        # --- INTERACTION ---
        if event and "selection" in event and event["selection"]["points"]:
            point = event["selection"]["points"][0]
            
            # 1. Update Coordinates
            if "lat" in point:
                clat, clon = point["lat"], point["lon"]
                st.session_state["selected_coords"] = {"lat": clat, "lon": clon}
                
                # BONUS: Fetch Elevation
                elev = utils.fetch_elevation(clat, clon)
                if elev: st.session_state["elevation"] = elev
                
            # 2. Update Region (Hit Testing)
            # We calculate this mathematically to bypass layer blocking
            if "lat" in point:
                clicked_area = get_clicked_area(point["lat"], point["lon"], geo_areas)
                if clicked_area and clicked_area in utils.CITIES:
                    if clicked_area != st.session_state["selected_price_area"]:
                        st.session_state["selected_price_area"] = clicked_area
                        st.rerun()

with c_info:
    st.info(f"""
    **Current Selection**
    
    ### {st.session_state['selected_price_area']}
    
    **Coordinates:**
    {st.session_state['selected_coords']['lat']:.4f}, {st.session_state['selected_coords']['lon']:.4f}
    """)
    
    if "elevation" in st.session_state:
        st.metric("Elevation", f"{st.session_state['elevation']} m")