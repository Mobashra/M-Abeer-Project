import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from shapely.geometry import shape, Point
import utils
from datetime import date
import branca.colormap as cm

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
# 2. CONTROLS (5 Columns)
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
            st.session_state["map_center"] = [city["lat"], city["lon"]]
            st.rerun()

st.divider()

# ======================================================
# 3. HELPER FUNCTIONS
# ======================================================
@st.cache_data
def get_geo_data():
    """Load both GeoJSONs once."""
    areas = utils.load_geojson()
    munis = utils.load_municipality_geojson()
    return areas, munis

def get_clicked_area(lat, lon, geojson_data):
    """Mathematical Hit Testing."""
    if not geojson_data: return None
    point = Point(lon, lat)
    for feature in geojson_data['features']:
        try:
            polygon = shape(feature['geometry'])
            if polygon.contains(point):
                props = feature['properties']
                # Try standard keys
                return props.get('ElSpotOmr') or props.get('ElSpot_omr')
        except:
            continue
    return None

# ======================================================
# 4. MAP LOGIC
# ======================================================
c_map, c_info = st.columns([3, 1])

with c_map:
    # 1. Fetch Data
    df = utils.load_map_stats(start_d, end_d, data_type, selected_group)
    geo_areas, geo_munis = get_geo_data()
    
    # 2. Setup Data Dictionary & Color Map
    data_dict = {}
    min_val, max_val = 0, 1
    
    if not df.empty:
        data_dict = df.set_index('price_area')['avg_value'].to_dict()
        min_val = df['avg_value'].min()
        max_val = df['avg_value'].max()

    # Create Viridis Color Scale (Like Plotly)
    colormap = cm.LinearColormap(
        colors=['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'], # Viridis Palette
        vmin=min_val,
        vmax=max_val,
        caption=f"Average {selected_group.capitalize()} (MWh)"
    )

    # 3. Initialize Map
    m = folium.Map(
        location=st.session_state["map_center"],
        zoom_start=st.session_state["map_zoom"],
        tiles="CartoDB positron",
        control_scale=True,
        zoom_control=True
    )
    
    # Add Color Legend to Map
    colormap.add_to(m)

    # 4. Style Function
    def style_function(feature):
        area_id = feature['properties'].get('ElSpotOmr') or feature['properties'].get('ElSpot_omr')
        
        # Color Logic
        fill_color = "#cccccc" # Default Grey
        if area_id and area_id in data_dict:
            fill_color = colormap(data_dict[area_id])
            
        # Highlight Logic
        color = "#555555"
        weight = 1
        opacity = 0.6
        
        if area_id == st.session_state["selected_price_area"]:
            color = "#ff0000" # Red Border for Selection
            weight = 3
            opacity = 0.8

        return {
            "fillColor": fill_color,
            "color": color,
            "weight": weight,
            "fillOpacity": opacity,
        }

    # 5. Layers Logic
    current_zoom = st.session_state["map_zoom"]
    
    # --- Price Areas (Base) ---
    if geo_areas:
        # Detect key for Price Area tooltip to prevent crash
        pa_props = geo_areas['features'][0]['properties']
        pa_key = 'ElSpotOmr' if 'ElSpotOmr' in pa_props else 'ElSpot_omr'
        
        folium.GeoJson(
            geo_areas,
            style_function=style_function,
            tooltip=folium.GeoJsonTooltip(fields=[pa_key], aliases=['Area:']),
            name="Price Areas"
        ).add_to(m)

    # --- Municipalities (Zoom Dependent) ---
    if current_zoom > 6 and geo_munis:
        # AUTO-DETECT KEY (The Fix for KeyError)
        muni_props = geo_munis['features'][0]['properties']
        muni_key = None
        if 'nummer' in muni_props: muni_key = 'nummer'
        elif 'kommunenummer' in muni_props: muni_key = 'kommunenummer'
        elif 'id' in muni_props: muni_key = 'id'
        
        # Only add layer if we found a valid key
        if muni_key:
            folium.GeoJson(
                geo_munis,
                style_function=lambda x: {
                    "fillColor": "transparent",
                    "color": "#000000",
                    "weight": 0.8,
                    "dashArray": "5, 5",
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=[muni_key], 
                    aliases=['Municipality ID:'],
                    sticky=False
                ),
                name="Municipalities"
            ).add_to(m)

    # 6. The Pointer
    if st.session_state["selected_coords"]:
        coords = st.session_state["selected_coords"]
        folium.Marker(
            [coords['lat'], coords['lon']],
            tooltip="Selected Location",
            icon=folium.Icon(color="red", icon="info-sign"),
        ).add_to(m)

    # 7. Render
    map_data = st_folium(
        m,
        height=750, 
        width="100%",
        returned_objects=["last_clicked", "zoom", "bounds"],
        key="folium_map"
    )

    # 8. Interaction Loop
    if map_data:
        # Zoom Update
        if map_data["zoom"] != st.session_state["map_zoom"]:
            st.session_state["map_zoom"] = map_data["zoom"]
            # Keep center
            bounds = map_data["bounds"]
            if bounds:
                lat = (bounds["_southWest"]["lat"] + bounds["_northEast"]["lat"]) / 2
                lng = (bounds["_southWest"]["lng"] + bounds["_northEast"]["lng"]) / 2
                st.session_state["map_center"] = [lat, lng]
            st.rerun()

        # Click Update
        if map_data["last_clicked"]:
            lat = map_data["last_clicked"]["lat"]
            lon = map_data["last_clicked"]["lng"]
            
            prev_lat = st.session_state["selected_coords"]["lat"]
            prev_lon = st.session_state["selected_coords"]["lon"]
            
            # If new click
            if abs(lat - prev_lat) > 0.0001 or abs(lon - prev_lon) > 0.0001:
                st.session_state["selected_coords"] = {"lat": lat, "lon": lon}
                
                # Hit Test Area
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