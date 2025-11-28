'''import streamlit as st
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
if not df.empty: df["price_area_map"] = df["price_area"].astype(str).str.replace("NO", "NO ")

def get_clicked_area_id(lat, lon, geo_data):
    """Robust Hit-Testing for Price Areas."""
    if not geo_data: return None
    point = Point(lon, lat)
    for f in geo_data['features']:
        try:
            if shape(f['geometry']).contains(point):
                return f['properties'].get('ElSpotOmr') or f['properties'].get('ElSpot_omr')
        except: continue
    return None

# --- CLICKABLE GRID (UPDATED: Finds Price Area) ---
clickable_points = []
if geojson_munis and geojson_areas:
    for f in geojson_munis['features']:
        try:
            geom = shape(f['geometry'])
            cent = geom.centroid
            
            # NEW LOGIC: Find which Price Area this centroid belongs to
            price_area_name = "Unknown"
            for area_f in geojson_areas['features']:
                area_geom = shape(area_f['geometry'])
                if area_geom.contains(cent):
                    price_area_name = area_f['properties'].get('ElSpotOmr') or area_f['properties'].get('ElSpot_omr')
                    break
            
            # Store the Price Area name instead of the Municipality name
            clickable_points.append({
                "lat": cent.y, 
                "lon": cent.x, 
                "name": price_area_name # <--- Now holds 'NO 1', 'NO 5' etc.
            })
        except: continue

df_clicks = pd.DataFrame(clickable_points)

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
        fig.update_traces(hovertemplate="<b>%{location}</b><extra></extra>")

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
                showscale=False, hoverinfo='text', text=names, 
                name="Municipalities"
            ))

    # --- LAYER 3: CLICK GRID (Invisible) ---
    if not df_clicks.empty:
        fig.add_trace(go.Scattermapbox(
            lat=df_clicks["lat"], lon=df_clicks["lon"],
            mode='markers', 
            marker=go.scattermapbox.Marker(size=12, color='white', opacity=0.01),
            hoverinfo='text', 
            text=df_clicks["name"], # Now shows "NO 1", "NO 2" etc. on hover
            name="Region"
        ))

    # --- LAYER 4: HIGHLIGHT ---
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

    fig.update_layout(margin=dict(r=0, t=0, l=0, b=0), clickmode='event+select', height=800, legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

    # --- INTERACTION ---
    if event and "selection" in event and event["selection"]["points"]:
        point = event["selection"]["points"][0]
        
        # 1. COORDS (From Grid or Pin)
        if "lat" in point:
            clat, clon = point["lat"], point["lon"]
            st.session_state["selected_coords"] = {"lat": clat, "lon": clon}
            
            # Elevation
            elev = utils.fetch_elevation(clat, clon)
            if elev is not None: st.session_state["elevation"] = elev
            
            # Hit Test Region
            hit_id = get_clicked_area_id(clat, clon, geojson_areas)
            if hit_id:
                # Clean ID: "NO 1" -> "NO1"
                clean = hit_id.replace(" ", "")
                if clean in utils.CITIES and clean != st.session_state["selected_price_area"]:
                    st.session_state["selected_price_area"] = clean
            st.rerun()

        # 2. REGION (Fallback)
        elif "location" in point:
            clicked = point["location"].replace(" ", "")
            if clicked in utils.CITIES and clicked != st.session_state["selected_price_area"]:
                st.session_state["selected_price_area"] = clicked
                st.rerun()

with c_info:
    st.markdown("#### 📌 Selection Status")
    with st.container(border=True):
        # 1. REGION INFO (Updated)
        curr = st.session_state["selected_price_area"]
        # Retrieve static center coordinates for this region from utils
        center = utils.CITIES[curr]
        
        st.info(f"**Active Region**\n# {curr}")
        st.caption(f"**Region Center:**\nLat {center['lat']:.4f}, Lon {center['lon']:.4f}")
        
        st.divider()
        
        # 2. PIN INFO
        if "selected_coords" in st.session_state:
            pin = st.session_state["selected_coords"]
            st.error(f"**📍 Pin Location**\n\nLat: {pin['lat']:.4f}\nLon: {pin['lon']:.4f}")
        
        # 3. ELEVATION (Custom Style)
        if "elevation" in st.session_state:
            st.markdown(f"""
                <div style="text-align: center; border: 1px solid #dcdcdc; padding: 10px; border-radius: 8px; background-color: #f9f9f9; margin-top: 10px;">
                    <span style="font-size: 1.1em; color: #555;">⛰️ Elevation</span>
                    <h2 style="margin: 0; color: #004d40; font-size: 2em;">{st.session_state['elevation']} m</h2>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("Click map to fetch elevation.")'''




import streamlit as st
import pandas as pd
import json
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
from shapely.geometry import shape, Point
import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Map & Data Selector",
    layout="wide"
)

# MongoDB connection
@st.cache_resource
def init_connection():
    """Initialize MongoDB connection using secrets"""
    try:
        uri = st.secrets["URI"]
        client = MongoClient(uri, server_api=ServerApi('1'))
        return client
    except Exception:
        return None

# Fetch energy stats from MongoDB
@st.cache_data(ttl=3600)
def fetch_energy_stats(start_date_str, end_date_str, group):
    """
    Fetch aggregated energy stats for all price areas for the given time range and group.
    Returns a dictionary {area_name: mean_value}
    """
    client = init_connection()
    if not client:
        return {}
    
    try:
        db = client['energy_data']
        collection_name = 'production' if group == 'Production' else 'consumption'
        collection = db[collection_name]
        
        pipeline = [
            {
                "$match": {
                    "startTime": {"$gte": start_date_str, "$lte": end_date_str}
                }
            },
            {
                "$group": {
                    "_id": "$priceArea",
                    "mean_value": {"$avg": "$quantityKwh"}
                }
            }
        ]
        
        results = list(collection.aggregate(pipeline))
        stats = {res['_id']: res['mean_value'] for res in results}
        return stats
        
    except Exception as e:
        st.error(f"Database error: {e}")
        return {}

# Initialize session state variables
if 'selected_coordinates' not in st.session_state:
    st.session_state.selected_coordinates = None
if 'selected_price_area' not in st.session_state:
    st.session_state.selected_price_area = None
if 'weather_data' not in st.session_state:
    st.session_state.weather_data = None
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 5
if 'map_center' not in st.session_state:
    st.session_state.map_center = [65.0, 13.0]
elif isinstance(st.session_state.map_center, dict):
    st.session_state.map_center = [st.session_state.map_center['lat'], st.session_state.map_center['lon']]
if 'last_clicked_processed' not in st.session_state:
    st.session_state.last_clicked_processed = None

# Load GeoJSON data
@st.cache_data
def load_geojsons():
    price_area_path = 'ElSpot_omraade.geojson'
    kommune_path = 'Basisdata_0000_Norge_4258_Kommune_GeoJSON.geojson'
    
    data = {}
    if os.path.exists(price_area_path):
        with open(price_area_path, 'r', encoding='utf-8-sig') as f:
            data['price_area'] = json.load(f)
            
            # Pre-process: ensure IDs are set
            for feature in data['price_area']['features']:
                props = feature['properties']
                name = props.get('ElSpotOmr') or props.get('omrnavn') or props.get('navn') or props.get('name')
                if name:
                    name = name.replace(" ", "")
                feature['id'] = name
                props['name'] = name
            
    if os.path.exists(kommune_path):
        with open(kommune_path, 'r', encoding='utf-8-sig') as f:
            data['kommune'] = json.load(f)
            
            # Pre-process: Map Municipalities to Price Areas for coloring
            price_polygons = []
            if 'price_area' in data:
                for feature in data['price_area']['features']:
                    poly = shape(feature['geometry'])
                    name = feature.get('id')
                    price_polygons.append((poly, name))
            
            # Map each municipality to its price area
            if 'features' in data['kommune']:
                for i, feature in enumerate(data['kommune']['features']):
                    props = feature.get('properties', {})
                    
                    if 'id' not in feature:
                        feature['id'] = props.get('kommunenummer', str(i))
                    
                    try:
                        geom = shape(feature['geometry'])
                        centroid = geom.centroid
                        for poly, area_name in price_polygons:
                            if poly.contains(centroid):
                                props['price_area'] = area_name
                                break
                    except Exception:
                        pass
            
    return data

# Helper function to find which price area a point is in
def find_price_area_for_point(lat, lon, price_area_data):
    """Find which price area a point is in"""
    point = Point(lon, lat)  # Point takes (x, y) = (lon, lat)
    
    if price_area_data:
        for feature in price_area_data['features']:
            try:
                poly = shape(feature['geometry'])
                if poly.contains(point):
                    return feature.get('id')
            except Exception:
                pass
    return None

from utils import download_weather_data, render_sidebar_info

# Render sidebar data info
render_sidebar_info()

# Main Layout
st.title("📍 Map & Data Selector")
st.markdown("Click anywhere on the map to select a location and its Price Area.")

col_controls, col_map = st.columns([1, 2])

geojson_data = load_geojsons()
price_area_data = geojson_data.get('price_area')
kommune_data = geojson_data.get('kommune')

with col_controls:
    st.subheader("1. Map Configuration")
    st.caption("Configure the energy data displayed on the map.")
    
    # Energy Group Selector
    energy_group = st.selectbox(
        "Energy Group",
        options=["Production", "Consumption"],
        help="Select energy data type to visualize on the map"
    )
    
    # Time Interval Selector
    time_interval = st.number_input(
        "Time Interval (Days)",
        min_value=1,
        max_value=365,
        value=30,
        help="Interval for calculating mean energy values"
    )
    
    # Analysis Date Selector
    default_date = datetime(2024, 1, 1).date()
    analysis_date = st.date_input(
        "Map Data Start Date",
        value=default_date,
        help="Select the start date for the map visualization interval"
    )

with col_map:
    st.subheader("Interactive Map")
    st.caption("Click to select location. Zoom in to see municipalities, zoom out for price areas.")
    
    # Calculate date range for stats
    stats_start_date = analysis_date
    stats_end_date = stats_start_date + timedelta(days=time_interval)
    
    stats_start_str = stats_start_date.strftime("%Y-%m-%dT00:00:00Z")
    stats_end_str = stats_end_date.strftime("%Y-%m-%dT23:59:59Z")
    
    # Fetch stats
    energy_stats = fetch_energy_stats(stats_start_str, stats_end_str, energy_group)
    
    # Get min/max for color scale
    if energy_stats:
        min_val = min(energy_stats.values())
        max_val = max(energy_stats.values())
    else:
        min_val, max_val = 0, 100
    
    # Create colormap (for styling polygons)
    colormap = cm.LinearColormap(
        colors=['#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C', '#FC4E2A', '#E31A1C', '#BD0026'],
        vmin=min_val,
        vmax=max_val
    )
    
    # Create a custom vertical legend HTML
    def create_vertical_legend(min_v, max_v, group_name):
        """Create a nice vertical color legend"""
        colors = ['#BD0026', '#E31A1C', '#FC4E2A', '#FD8D3C', '#FEB24C', '#FED976', '#FFEDA0']
        n_colors = len(colors)
        
        # Format values nicely
        def fmt(v):
            if v >= 1000000:
                return f'{v/1000000:.1f}M'
            elif v >= 1000:
                return f'{v/1000:.0f}k'
            else:
                return f'{v:.0f}'
        
        gradient_stops = ', '.join([f'{c} {i*100//(n_colors-1)}%' for i, c in enumerate(colors)])
        
        legend_html = f'''
        <div style="
            position: fixed;
            bottom: 50px;
            right: 20px;
            z-index: 1000;
            background: white;
            padding: 12px 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            font-family: Arial, sans-serif;
            font-size: 12px;
        ">
            <div style="font-weight: bold; margin-bottom: 8px; text-align: center; color: #333;">
                Mean {group_name}<br><span style="font-size: 10px; color: #666;">(kWh)</span>
            </div>
            <div style="display: flex; align-items: stretch;">
                <div style="
                    width: 20px;
                    height: 150px;
                    background: linear-gradient(to bottom, {gradient_stops});
                    border-radius: 3px;
                    border: 1px solid #ccc;
                "></div>
                <div style="
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    margin-left: 8px;
                    padding: 2px 0;
                    color: #444;
                ">
                    <span>{fmt(max_v)}</span>
                    <span>{fmt((max_v + min_v) / 2)}</span>
                    <span>{fmt(min_v)}</span>
                </div>
            </div>
        </div>
        '''
        return legend_html
    
    # Create Folium map
    map_center = st.session_state.map_center
    m = folium.Map(
        location=map_center,
        zoom_start=st.session_state.map_zoom,
        tiles='cartodbpositron'
    )
    
    # Get selected price area for highlighting
    selected_area = st.session_state.selected_price_area
    
    # Zoom threshold for switching layers
    ZOOM_THRESHOLD = 7
    current_zoom = st.session_state.map_zoom
    
    # Style function for Price Areas - highlight selected area
    def price_area_style(feature):
        area_id = feature.get('id') or feature['properties'].get('name')
        value = energy_stats.get(area_id, 0)
        is_selected = (area_id == selected_area)
        
        return {
            'fillColor': colormap(value) if value else '#gray',
            'color': '#0000FF' if is_selected else '#000000',  # Blue outline if selected
            'weight': 4 if is_selected else 2,
            'fillOpacity': 0.6 if is_selected else 0.5
        }
    
    # Style function for Municipalities
    def municipality_style(feature):
        props = feature.get('properties', {})
        price_area = props.get('price_area')
        value = energy_stats.get(price_area, 0) if price_area else 0
        is_selected = (price_area == selected_area)
        
        return {
            'fillColor': colormap(value) if value else '#gray',
            'color': '#0000FF' if is_selected else '#333333',  # Blue outline if in selected area
            'weight': 2 if is_selected else 1,
            'fillOpacity': 0.6 if is_selected else 0.5
        }
    
    # Conditionally add layer based on zoom level
    if current_zoom >= ZOOM_THRESHOLD:
        # Zoomed in - show municipalities
        if kommune_data:
            folium.GeoJson(
                kommune_data,
                name='municipalities_layer',
                style_function=municipality_style,
                tooltip=folium.GeoJsonTooltip(
                    fields=['kommunenavn', 'price_area'],
                    aliases=['Municipality:', 'Price Area:'],
                    localize=True
                )
            ).add_to(m)
    else:
        # Zoomed out - show price areas
        if price_area_data:
            folium.GeoJson(
                price_area_data,
                name='price_areas_layer',
                style_function=price_area_style,
                tooltip=folium.GeoJsonTooltip(
                    fields=['name'],
                    aliases=['Price Area:'],
                    localize=True
                )
            ).add_to(m)
    
    # Add custom vertical legend to map
    legend_html = create_vertical_legend(min_val, max_val, energy_group)
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add marker for selected location
    if st.session_state.selected_coordinates:
        lat, lon = st.session_state.selected_coordinates
        popup_text = f"""
        <b>Selected Location</b><br>
        Price Area: {st.session_state.selected_price_area or 'Unknown'}<br>
        Lat: {lat:.4f}<br>
        Lon: {lon:.4f}
        """
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=200),
            icon=folium.Icon(color='red', icon='info-sign'),
            tooltip=f"Price Area: {st.session_state.selected_price_area or 'Unknown'}"
        ).add_to(m)
    
    # Render the map and capture click events
    map_data = st_folium(
        m,
        width=None,
        height=600,
        returned_objects=["last_clicked", "zoom", "bounds"],
        use_container_width=True,
        key="main_map"
    )
    
    # Handle click events - only rerun on actual clicks
    need_rerun = False
    
    if map_data and map_data.get('last_clicked'):
        clicked_lat = map_data['last_clicked']['lat']
        clicked_lon = map_data['last_clicked']['lng']
        click_key = (round(clicked_lat, 6), round(clicked_lon, 6))
        
        # Check if this click has already been processed
        if click_key != st.session_state.last_clicked_processed:
            st.session_state.last_clicked_processed = click_key
            
            # Find which price area the click is in
            price_area = find_price_area_for_point(clicked_lat, clicked_lon, price_area_data)
            
            # Update session state
            st.session_state.selected_coordinates = (clicked_lat, clicked_lon)
            st.session_state.selected_price_area = price_area
            st.session_state.map_center = [clicked_lat, clicked_lon]
            
            # Update zoom if returned
            if map_data.get('zoom'):
                st.session_state.map_zoom = map_data['zoom']
            
            need_rerun = True
    
    # Check if zoom crossed threshold (for layer switching)
    if map_data and map_data.get('zoom'):
        new_zoom = map_data['zoom']
        old_zoom = st.session_state.map_zoom
        
        # Check if zoom crossed the threshold
        crossed_threshold = (old_zoom < ZOOM_THRESHOLD and new_zoom >= ZOOM_THRESHOLD) or \
                           (old_zoom >= ZOOM_THRESHOLD and new_zoom < ZOOM_THRESHOLD)
        
        if crossed_threshold:
            st.session_state.map_zoom = new_zoom
            # Calculate center from bounds to preserve map position
            if map_data.get('bounds'):
                bounds = map_data['bounds']
                center_lat = (bounds['_southWest']['lat'] + bounds['_northEast']['lat']) / 2
                center_lng = (bounds['_southWest']['lng'] + bounds['_northEast']['lng']) / 2
                st.session_state.map_center = [center_lat, center_lng]
            need_rerun = True
    
    if need_rerun:
        st.rerun()

with col_controls:
    st.markdown("---")
    st.subheader("2. Weather Data Download")
    st.caption("Configure and download historical weather data for the selected location.")
    
    # Year Range Selector
    current_year = 2024
    years = list(range(2021, current_year + 1))
    
    col_y1, col_y2 = st.columns(2)
    with col_y1:
        start_year = st.selectbox("Start Year", options=years, index=0)
    with col_y2:
        end_year = st.selectbox("End Year", options=years, index=len(years)-1)

    if start_year > end_year:
        st.error("Start year must be before End year")
    
    st.markdown("---")
    
    # Display current selection info
    if st.session_state.selected_coordinates:
        lat, lon = st.session_state.selected_coordinates
        st.info(f"📍 **Coordinates:** {lat:.4f}, {lon:.4f}")
    else:
        st.warning("Click on the map to select a location.")
        
    if st.session_state.selected_price_area:
        st.success(f"⚡ **Price Area:** {st.session_state.selected_price_area}")
    
    # Download Button
    if st.button("📥 Download Weather Data", type="primary", disabled=not st.session_state.selected_coordinates):
        if st.session_state.selected_coordinates and start_year <= end_year:
            lat, lon = st.session_state.selected_coordinates
            with st.spinner(f"Downloading weather data for {start_year}-{end_year}..."):
                try:
                    weather_df = download_weather_data(lat, lon, start_year, end_year)
                    st.session_state.weather_data = weather_df
                    st.session_state.data_range = (start_year, end_year)
                    st.session_state.weather_data_area = st.session_state.selected_price_area
                    st.success(f"✅ Loaded {len(weather_df)} records ({start_year}-{end_year})!")
                except Exception as e:
                    st.error(f"Error downloading data: {e}")