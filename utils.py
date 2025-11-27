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

# --- 2. DATABASE CONNECTION ---
@st.cache_resource
def get_mongo_collection(collection_name=None):
    """Connects to MongoDB and returns a collection object."""
    try:
        client = MongoClient(st.secrets["mongo"]["uri"])
        db = client[st.secrets["mongo"]["database"]]
        if collection_name:
            return db[collection_name]
        return db[st.secrets["mongo"]["collection"]]
    except Exception as e:
        st.error(f"MongoDB Connection Error: {e}")
        return None

# --- 3. LOADERS ---
@st.cache_data(ttl=3600)
def load_yearly_data(data_type, year):
    """
    Fetches raw data for ONE year for energy analysis.
    Returns: DataFrame with columns ['date', 'group', 'price_area', 'mwh']
    """
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"

    coll = get_mongo_collection(coll_name)
    if coll is None:
        return pd.DataFrame()

    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31, 23, 59, 59)
    query = {"start_time": {"$gte": start_date, "$lte": end_date}}

    projection = {"price_area": 1, group_col: 1, "start_time": 1, "value": 1, "_id": 0}
    data = list(coll.find(query, projection).limit(300000))
    df = pd.DataFrame(data)
    if df.empty:
        return df

    df.rename(columns={group_col: 'group', 'start_time': 'date', 'value': 'mwh'}, inplace=True)
    df['group'] = df['group'].astype(str).fillna("Unknown")
    df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_convert("Europe/Oslo")
    return df

# Alias for backward compatibility
get_year_data = load_yearly_data

@st.cache_data(ttl=3600)
def load_map_data(target_year, days_to_agg, data_type, selected_group):
    """
    Returns aggregated mean values for the map (Home Page).
    """
    if data_type == "Production":
        coll = get_mongo_collection(st.secrets["mongo"]["collection"])
        group_col = "production_group"
    else:
        coll = get_mongo_collection(st.secrets["mongo"]["collection_cons"])
        group_col = "consumption_group"

    if coll is None:
        return pd.DataFrame()

    end_date = datetime(target_year, 12, 31, 23, 59)
    start_date = end_date - timedelta(days=days_to_agg)

    pipeline = [
        {"$match": {
            group_col: {"$regex": f"^{selected_group}$", "$options": "i"},
            "start_time": {"$gte": start_date, "$lte": end_date}
        }},
        {"$group": {
            "_id": "$price_area",
            "val": {"$avg": "$value"}
        }}
    ]
    data = list(coll.aggregate(pipeline))
    df = pd.DataFrame(data)
    if df.empty:
        return df

    df.rename(columns={'_id': 'price_area'}, inplace=True)
    df['price_area_map'] = df['price_area'].astype(str).str.replace("NO", "NO ")
    return df

# --- 4. LEGACY LOADER ---
@st.cache_data(ttl=600)
def load_elhub_data(year_filter=None):
    """
    Legacy loader for older pages.
    """
    coll = get_mongo_collection()
    if coll is None:
        return pd.DataFrame()

    query = {}
    if year_filter:
        s = datetime(year_filter, 1, 1)
        e = datetime(year_filter, 12, 31, 23, 59)
        query = {"start_time": {"$gte": s, "$lte": e}}

    data = list(coll.find(query, {"_id": 0}))
    df = pd.DataFrame(data)
    if not df.empty:
        df.rename(columns={"start_time": "date", "value": "mwh", "production_group": "group"}, inplace=True)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_convert("Europe/Oslo")
    return df

# --- 5. WEATHER API ---
@st.cache_data(ttl=3600)
def fetch_weather_api(lat, lon, start_date, end_date):
    """Fetch hourly weather from Open-Meteo ERA5 Archive."""
    hourly_vars = ",".join(WEATHER_VARS)
    url = f"https://archive-api.open-meteo.com/v1/era5?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&hourly={hourly_vars}&timezone=Europe/Oslo"
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        js = resp.json()
        if "hourly" not in js:
            return pd.DataFrame()
        df = pd.DataFrame(js["hourly"])
        df["time"] = pd.to_datetime(df["time"])
        return df
    except Exception:
        return pd.DataFrame()

# --- 6. GEOJSON ---
@st.cache_data(ttl=3600)
def load_geojson():
    """Load GeoJSON of price areas."""
    try:
        with open('elspot_areas.geojson', 'r') as f:
            return json.load(f)
    except Exception:
        return None
