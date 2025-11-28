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
    try:
        # Check if secrets exist
        if "mongo" not in st.secrets:
            return None
        
        client = MongoClient(st.secrets["mongo"]["uri"])
        db = client[st.secrets["mongo"]["database"]]
        if collection_name:
            return db[collection_name]
        else:
            return db[st.secrets["mongo"]["collection"]]
    except Exception as e:
        print(f"MongoDB Connection Error: {e}")
        return None

# --- 3. DATA LOADERS ---

@st.cache_data(ttl=3600)
def load_map_stats(year, days_range, data_type, selected_group):
    """
    Aggregates average Energy values per Price Area for the Map Choropleth.
    """
    # Determine Collection
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"

    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()

    # Time Filter
    start_date = datetime(year, 1, 1)
    end_date = start_date + timedelta(days=days_range)

    # Aggregation Pipeline
    pipeline = [
        {
            "$match": {
                "start_time": {"$gte": start_date, "$lte": end_date},
                group_col: selected_group
            }
        },
        {
            "$group": {
                "_id": "$price_area", # Group by NO1, NO2...
                "avg_value": {"$avg": "$value"} # Calculate Mean
            }
        }
    ]

    try:
        data = list(coll.aggregate(pipeline))
        df = pd.DataFrame(data)
        if df.empty: return df

        df.rename(columns={'_id': 'price_area'}, inplace=True)
        return df
    except Exception as e:
        print(f"Aggregation Error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_yearly_data(data_type, year):
    """Fetches raw hourly data for charts."""
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
    
    # Optimization: Only fetch needed fields
    projection = {"price_area": 1, group_col: 1, "start_time": 1, "value": 1, "_id": 0}
    
    query = {"start_time": {"$gte": start_date, "$lte": end_date}}
    
    # Limit to prevent memory crash
    data = list(coll.find(query, projection).limit(500000)) 
    df = pd.DataFrame(data)

    if not df.empty:
        df.rename(columns={group_col: 'group', 'start_time': 'date', 'value': 'mwh'}, inplace=True)
        
        # Safe Timezone Conversion
        df['date'] = pd.to_datetime(df['date'], utc=True)
        df['date'] = df['date'].dt.tz_convert("Europe/Oslo")

    return df

# Legacy aliases
get_year_data = load_yearly_data
load_elhub_data = load_yearly_data 

# --- 4. API & GEOJSON ---

@st.cache_data(ttl=3600)
def fetch_weather_api(lat, lon, start_date, end_date):
    """Fetch Open-Meteo Data."""
    hourly_vars = ",".join(WEATHER_VARS)
    url = f"https://archive-api.open-meteo.com/v1/era5?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&hourly={hourly_vars}&timezone=Europe/Oslo"
    
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        js = resp.json()
        
        if "hourly" not in js: return pd.DataFrame()
        
        df = pd.DataFrame(js["hourly"])
        if "time" in df.columns:
             df["time"] = pd.to_datetime(df["time"])
        
        return df
    except Exception as e:
        print(f"API Error: {e}")
        return pd.DataFrame()

@st.cache_data
def load_geojson():
    """Loads the Price Area polygons (elspot_areas.geojson)."""
    try:
        with open('elspot_areas.geojson', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

@st.cache_data
def load_municipality_geojson():
    """Loads the specific Norwegian Municipality file you uploaded."""
    filename = 'Basisdata_0000_Norge_4258_Kommune_GeoJSON.geojson'
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None