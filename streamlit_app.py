import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from shapely.geometry import shape, Point
import utils
from datetime import date
import json

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
if "map_zoom" not in st.session_state:
    st.session_state["map_zoom"] = 5
if "map_center" not in st.session_state:
    st.session_state["map_center"] = [65.0, 15.0]

current_area = st.session_state["selected_price_area"]

# ======================================================
# 2. CONTROLS (5 Columns for Perfect Alignment)
# ======================================================
with st.container():
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown("###### 1. Source")
        data_type = st.radio("Source", ["Production", "Consumption"], horizontal=True, label_visibility="collapsed")

    with c2:
        st.markdown("###### 2. Start Date")
        # Default 2021
        start_d = st.date_input("Start", date(2021, 1, 1), min_value=date(2021, 1, 1), max_value=date(2024, 12, 31), label_visibility="collapsed")

    with c3:
        st.markdown("###### 3. End Date")
        # Default 2021
        end_d = st.date_input("End", date(2021, 12, 31), min_value=date(2021, 1, 1), max_value=date(2024, 12, 31), label_visibility="collapsed")

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
            # Move map to selection
            st.session_state["map_center"] = [city["lat"], city["lon"]]
            st.rerun()

st.divider()

# ======================================================
# 3. HELPER FUNCTIONS (Geometric Logic)
# ======================================================
@st.cache_data
def get_geo_data():
    """Load both GeoJSONs once."""
    areas = utils.load_geojson()
    munis = utils.load_municipality_geojson()
    return areas, munis

def get_clicked_area(lat, lon, geojson_data):
    """
    Mathematical Hit Testing:
    Checks which Polygon actually contains the clicked Point.
    This works even if visual layers (like Municipalities) block the click.
    """
    if not geojson_data: return None
    point = Point(lon, lat)
    for feature in geojson_data['features']:
        try:
            polygon = shape(feature['geometry'])
            if polygon.contains(point):
                # Try to find the ID (ElSpotOmr or ElSpot_omr)
                props = feature['properties']
                return props.get('ElSpotOmr') or props.get('ElSpot_omr')
        except:
            continue
    return None

# ======================================================
# 4. MAP LOGIC
# ======================================================
# Changed Ratio: [3, 1] gives a wider map area, fitting Norway's length better when we increase height
c_map, c_info = st.columns([3, 1])

with c_map:
    # 1. Fetch Data
    df = utils.load_map_stats(start_d, end_d, data_type, selected_group)
    geo_areas, geo_munis = get_geo_data()
    
    # Create Data Dict for Coloring {NO1: 1234.5, ...}
    data_dict = {}
    if not df.empty:
        data_dict = df.set_index('price_area')['avg_value'].to_dict()

    # 2. Initialize Folium Map
    m = folium.Map(
        location=st.session_state["map_center"],
        zoom_start=st.session_state["map_zoom"],
        tiles="CartoDB positron",
        control_scale=True,
        zoom_control=True
    )

    # 3. Style Function (Coloring Logic)
    def style_function(feature):
        area_id = feature['properties'].get('ElSpotOmr') or feature['properties'].get('ElSpot_omr')
        
        # Default Styles
        fill_color = "#f0f0f0"
        weight = 1
        color = "#666666"
        opacity = 0.5
        
        # Color by Data
        if area_id and area_id in data_dict:
            val = data_dict[area_id]
            max_val = max(data_dict.values()) if data_dict else 1
            # Normalize 0-1
            intensity = val / max_val
            
            # Manual Blue Scale (Gradient)
            if intensity > 0.8: fill_color = "#084594"
            elif intensity > 0.6: fill_color = "#2171b5"
            elif intensity > 0.4: fill_color = "#4292c6"
            elif intensity > 0.2: fill_color = "#9ecae1"
            else: fill_color = "#deebf7"
            
        # Highlight Selected Area
        if area_id == st.session_state["selected_price_area"]:
            color = "#ff0000" # Red Border
            weight = 3
            opacity = 0.7

        return {
            "fillColor": fill_color,
            "color": color,
            "weight": weight,
            "fillOpacity": opacity,
        }

    # 4. Zoom-Dependent Layers (Bonus Implementation)
    current_zoom = st.session_state["map_zoom"]
    
    # Always add Price Areas (Base Layer)
    if geo_areas:
        folium.GeoJson(
            geo_areas,
            style_function=style_function,
            tooltip=folium.GeoJsonTooltip(
                fields=['ElSpotOmr'],
                aliases=['Price Area:'],
                localize=True
            ),
            name="Price Areas"
        ).add_to(m)

    # Add Municipalities ONLY if zoomed in (Zoom > 6)
    if current_zoom > 6 and geo_munis:
        folium.GeoJson(
            geo_munis,
            style_function=lambda x: {
                "fillColor": "transparent", # Transparent fill
                "color": "#333333",         # Dark Grey border
                "weight": 0.8,
                "dashArray": "5, 5",        # Dashed line
            },
            # Tooltip with correct name parsing
            tooltip=folium.GeoJsonTooltip(
                # We assume the name is in 'navn' or 'kommunenavn'
                # Note: Folium tooltips are simpler than Plotly's. 
                # If 'navn' is a complex object, it might show raw text.
                # However, this usually works for standard Geonorge files.
                fields=['kommunenummer'], 
                aliases=['Muni ID:'],
                sticky=False
            ),
            name="Municipalities"
        ).add_to(m)

    # 5. The Pointer (Marker)
    if st.session_state["selected_coords"]:
        coords = st.session_state["selected_coords"]
        folium.Marker(
            [coords['lat'], coords['lon']],
            tooltip="Selected Location",
            icon=folium.Icon(color="red", icon="info-sign"),
        ).add_to(m)

    # 6. Render Map
    # height=750 makes it "Longer" as requested
    map_data = st_folium(
        m,
        height=750, 
        width="100%",
        returned_objects=["last_clicked", "zoom", "bounds"],
        key="folium_map"
    )

    # 7. Interaction Logic
    if map_data:
        # A. Detect Zoom Change
        if map_data["zoom"] != st.session_state["map_zoom"]:
            st.session_state["map_zoom"] = map_data["zoom"]
            # Save center to prevent resetting view
            bounds = map_data["bounds"]
            if bounds:
                lat = (bounds["_southWest"]["lat"] + bounds["_northEast"]["lat"]) / 2
                lng = (bounds["_southWest"]["lng"] + bounds["_northEast"]["lng"]) / 2
                st.session_state["map_center"] = [lat, lng]
            st.rerun()

        # B. Detect Click
        if map_data["last_clicked"]:
            lat = map_data["last_clicked"]["lat"]
            lon = map_data["last_clicked"]["lng"]
            
            # Check if it's a NEW click (Float comparison with small tolerance)
            prev_lat = st.session_state["selected_coords"]["lat"]
            prev_lon = st.session_state["selected_coords"]["lon"]
            
            if abs(lat - prev_lat) > 0.0001 or abs(lon - prev_lon) > 0.0001:
                
                # 1. Update Coordinates (Pointer)
                st.session_state["selected_coords"] = {"lat": lat, "lon": lon}
                
                # 2. Hit Test: Calculate which Price Area was clicked
                # This fixes the "Blocked Click" issue
                clicked_area = get_clicked_area(lat, lon, geo_areas)
                
                if clicked_area and clicked_area in utils.CITIES:
                    if clicked_area != st.session_state["selected_price_area"]:
                        st.session_state["selected_price_area"] = clicked_area
                
                st.rerun()

with c_info:
    st.info(f"""
    **Active Selection**
    
    ### {st.session_state['selected_price_area']}
    
    **Pin Location:**
    
    Lat: {st.session_state['selected_coords']['lat']:.4f}
    
    Lon: {st.session_state['selected_coords']['lon']:.4f}
    """)
    
    st.markdown("#### 🗺️ Map Guide")
    st.markdown("""
    * **Zoom Out:** View colored Price Areas.
    * **Zoom In (+):** Detailed Municipality borders appear automatically.
    * **Click:** Drops a **Red Pin** and auto-selects the region.
    """)
    
    # Legend
    st.caption("Color Scale (MWh)")
    st.markdown(
        """
        <div style="background: linear-gradient(to right, #deebf7, #084594); height: 10px; width: 100%; border-radius: 5px;"></div>
        <div style="display: flex; justify-content: space-between; font-size: 12px;">
            <span>Low</span>
            <span>High</span>
        </div>
        """, 
        unsafe_allow_html=True
    )