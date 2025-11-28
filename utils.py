import streamlit as st
import pandas as pd
import requests
import json
from pymongo import MongoClient
from datetime import datetime, timedelta

# --- 1. CONSTANTS ---
CITIES = {
    "NO1": {"city": "Oslo", "lat": 59.9139, "lon": 10.7522},
    "NO2": {"city": "Kristiansand", "lat": 58.1467, "lon": 7.9956},
    "NO3": {"city": "Trondheim", "lat": 63.4305, "lon": 10.3951},
    "NO4": {"city": "Tromsø", "lat": 69.6492, "lon": 18.9553},
    "NO5": {"city": "Bergen", "lat": 60.3942, "lon": 5.3221},
}

WEATHER_VARS = ["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]

# --- 2. SIDEBAR STYLING ---
SIDEBAR_CSS = """
<style>
    [data-testid="stSidebarNav"] li:has(a[href*="Map_Selector"]) span,
    [data-testid="stSidebarNav"] li:has(a[href*="Energy_Stats"]) span,
    [data-testid="stSidebarNav"] li:has(a[href*="Weather_Stats"]) span {
        background: linear-gradient(90deg, #1e3a5f 0%, #2d5a87 100%);
        color: white !important; padding: 4px 10px; border-radius: 6px; margin-bottom: 4px; display: block;
    }
    [data-testid="stSidebarNav"] li:has(a[href*="Correlations"]) span,
    [data-testid="stSidebarNav"] li:has(a[href*="Anomalies"]) span,
    [data-testid="stSidebarNav"] li:has(a[href*="Signal_Processing"]) span {
        background: linear-gradient(90deg, #1a472a 0%, #2d6a4f 100%);
        color: white !important; padding: 4px 10px; border-radius: 6px; margin-bottom: 4px; display: block;
    }
    [data-testid="stSidebarNav"] li:has(a[href*="Snow_Drift"]) span,
    [data-testid="stSidebarNav"] li:has(a[href*="Forecasting"]) span {
        background: linear-gradient(90deg, #4a1a6b 0%, #6b2d8a 100%);
        color: white !important; padding: 4px 10px; border-radius: 6px; margin-bottom: 4px; display: block;
    }
</style>
"""

def render_sidebar():
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.header("⚡ Energy Atlas")
        st.markdown("---")
        if "selected_price_area" in st.session_state:
            st.success(f"**Region:** {st.session_state['selected_price_area']}")
        if "selected_coords" in st.session_state:
            c = st.session_state["selected_coords"]
            st.caption(f"Lat: {c['lat']:.2f}, Lon: {c['lon']:.2f}")
        
        # Show Elevation in Sidebar too if available
        if "elevation" in st.session_state:
             st.caption(f"⛰️ Elevation: {st.session_state['elevation']}m")
             
        st.markdown("---")
        st.caption("Modules")
        st.markdown("🟦 **Explorative**")
        st.markdown("🟩 **Diagnostics**")
        st.markdown("🟪 **Predictive**")

def check_session_state():
    if "selected_price_area" not in st.session_state:
        st.error("⛔ **No Region Selected**")
        st.info("Please select a region from the **Map Selector** page first.")
        if st.button("Go to Map"): st.switch_page("pages/01_Map_Selector.py")
        st.stop()

# --- 3. DATA LOADERS ---
@st.cache_resource
def get_mongo_collection(collection_name=None):
    if "mongo" not in st.secrets: return None
    try:
        client = MongoClient(st.secrets["mongo"]["uri"])
        db = client[st.secrets["mongo"]["database"]]
        return db[collection_name] if collection_name else db[st.secrets["mongo"]["collection"]]
    except: return None

@st.cache_data(ttl=3600)
def load_map_stats(start_date, end_date, data_type, selected_group):
    coll_name = st.secrets["mongo"].get("collection", "production_mba_hour") if data_type == "Production" else st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
    group_col = "production_group" if data_type == "Production" else "consumption_group"
    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()
    
    s_dt = datetime.combine(start_date, datetime.min.time())
    e_dt = datetime.combine(end_date, datetime.max.time())
    pipeline = [{"$match": {"start_time": {"$gte": s_dt, "$lte": e_dt}, group_col: selected_group}}, {"$group": {"_id": "$price_area", "avg_value": {"$avg": "$value"}}}]
    try:
        data = list(coll.aggregate(pipeline))
        df = pd.DataFrame(data)
        if df.empty: return df
        df.rename(columns={'_id': 'price_area'}, inplace=True)
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_yearly_data(data_type, year):
    coll_name = st.secrets["mongo"].get("collection", "production_mba_hour") if data_type == "Production" else st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
    group_col = "production_group" if data_type == "Production" else "consumption_group"
    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()
    
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31, 23, 59, 59)
    projection = {"price_area": 1, group_col: 1, "start_time": 1, "value": 1, "_id": 0}
    try:
        data = list(coll.find({"start_time": {"$gte": start_date, "$lte": end_date}}, projection).limit(500000))
        df = pd.DataFrame(data)
        if not df.empty:
            df.rename(columns={group_col: 'group', 'start_time': 'date', 'value': 'mwh'}, inplace=True)
            df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_convert("Europe/Oslo")
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_weather_api(lat, lon, start_date, end_date):
    hourly_vars = ",".join(WEATHER_VARS)
    url = f"https://archive-api.open-meteo.com/v1/era5?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&hourly={hourly_vars}&timezone=Europe/Oslo"
    try:
        resp = requests.get(url, timeout=10); resp.raise_for_status(); js = resp.json()
        if "hourly" not in js: return pd.DataFrame()
        df = pd.DataFrame(js["hourly"])
        if "time" in df.columns: df["time"] = pd.to_datetime(df["time"])
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=3600*24)
def fetch_elevation(lat, lon):
    """
    Robust elevation lookup system:
    1. Open-Meteo elevation API
    2. Open-Meteo reverse geocoding elevation (better fallback)
    3. Mapbox Terrain-RGB (optional, if token exists)
    """

    # --- 1) Try Open-Meteo elevation API ---
    try:
        r = requests.get(
            f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}",
            timeout=5
        )
        r.raise_for_status()
        js = r.json()
        elev = js.get("elevation", [None])[0]
        if elev is not None:
            return round(elev)
    except:
        pass

    # --- 2) Try Reverse Geocoding Elevation (More reliable) ---
    try:
        r = requests.get(
            f"https://geocoding-api.open-meteo.com/v1/reverse?latitude={lat}&longitude={lon}",
            timeout=5
        )
        r.raise_for_status()
        js = r.json()
        if "elevation" in js and js["elevation"] is not None:
            return round(js["elevation"])
    except:
        pass

    # --- 3) Try Mapbox Terrain-RGB tile query (optional) ---
    token = st.secrets.get("mapbox", {}).get("token", None)
    if token:
        try:
            # Convert lat/lon to Web Mercator pixel for Terrain-RGB
            import math

            z = 14
            lat_rad = math.radians(lat)
            n = 2.0 ** z
            x = int((lon + 180.0) / 360.0 * n)
            y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)

            url = f"https://api.mapbox.com/v4/mapbox.terrain-rgb/{z}/{x}/{y}.pngraw?access_token={token}"
            img = requests.get(url, timeout=5)
            img.raise_for_status()

            from PIL import Image
            import numpy as np
            from io import BytesIO

            im = Image.open(BytesIO(img.content))
            pix = np.array(im)[im.size[1]//2, im.size[0]//2]  # center pixel = local elevation point
            R, G, B = pix[:3]

            elevation = -10000 + (R * 256 * 256 + G * 256 + B) * 0.1
            return round(elevation)

        except:
            pass

    # Could not determine elevation
    return None


@st.cache_data
def load_geojson():
    try: 
        with open('elspot_areas.geojson', 'r', encoding='utf-8') as f: return json.load(f)
    except: return None

@st.cache_data
def load_municipality_geojson():
    try: 
        with open('Basisdata_0000_Norge_4258_Kommune_GeoJSON.geojson', 'r', encoding='utf-8-sig') as f: return json.load(f)
    except: return None