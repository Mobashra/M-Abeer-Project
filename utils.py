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

# --- 2. SESSION & UI HELPERS ---

def check_session_state():
    """
    Enforces the rule: User MUST select an area on the map first.
    """
    # Check if the key exists and is not None
    if "selected_price_area" not in st.session_state or not st.session_state["selected_price_area"]:
        st.error("⛔ **Context Missing**")
        st.warning("Please select a Region on the Map page first.")
        
        # Link to the Map Page (Ensure the file exists in pages/)
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("Go to Map Selector"):
                st.switch_page("pages/01_Map_Selector.py")
        
        st.stop() # Stop execution here

def render_sidebar():
    """
    Renders the Global Context sidebar (Read-Only Info).
    """
    with st.sidebar:
        st.header("⚡ Energy Atlas")
        st.caption("v2.0 Professional Edition")
        st.divider()
        
        # Global Context Info
        if "selected_price_area" in st.session_state and st.session_state["selected_price_area"]:
            st.markdown("### 🌍 Active Context")
            st.success(f"**Region:** {st.session_state['selected_price_area']}")
            
            coords = st.session_state.get("selected_coords", {"lat": 0, "lon": 0})
            st.code(f"{coords['lat']:.4f}, {coords['lon']:.4f}", language="json")
            
            # Bonus: Elevation
            if "elevation" in st.session_state:
                st.caption(f"⛰️ Elevation: {st.session_state['elevation']}m")
        else:
            st.warning("⚠️ No Selection")
            st.caption("Use the Map to select a region.")

        st.divider()
        
        # Navigation Groups (Visual Guide Only)
        st.caption("Modules")
        st.markdown("🟦 **Exploration**")
        st.markdown("🟧 **Diagnostics**")
        st.markdown("🟪 **Predictive**")

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
    # Determine Collection
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"

    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()

    s_dt = datetime.combine(start_date, datetime.min.time())
    e_dt = datetime.combine(end_date, datetime.max.time())

    pipeline = [
        {"$match": {"start_time": {"$gte": s_dt, "$lte": e_dt}, group_col: selected_group}},
        {"$group": {"_id": "$price_area", "avg_value": {"$avg": "$value"}}}
    ]

    try:
        data = list(coll.aggregate(pipeline))
        df = pd.DataFrame(data)
        if df.empty: return df
        df.rename(columns={'_id': 'price_area'}, inplace=True)
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_yearly_data(data_type, year):
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"

    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()

    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31, 23, 59, 59)
    
    try:
        data = list(coll.find({"start_time": {"$gte": start_date, "$lte": end_date}}, 
                            {"price_area": 1, group_col: 1, "start_time": 1, "value": 1, "_id": 0}).limit(500000))
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
    """Bonus: Fetch elevation data."""
    try:
        r = requests.get(f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}", timeout=5)
        return r.json()["elevation"][0]
    except: return None

@st.cache_data
def load_geojson():
    try: 
        with open('elspot_areas.geojson', 'r', encoding='utf-8') as f: return json.load(f)
    except: return None

@st.cache_data
def load_municipality_geojson():
    try: 
        # utf-8-sig to handle BOM error
        with open('Basisdata_0000_Norge_4258_Kommune_GeoJSON.geojson', 'r', encoding='utf-8-sig') as f: return json.load(f)
    except: return None