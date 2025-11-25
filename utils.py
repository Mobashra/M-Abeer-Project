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
        client = MongoClient(st.secrets["mongo"]["uri"])
        db = client[st.secrets["mongo"]["database"]]
        if collection_name:
            return db[collection_name]
        else:
            return db[st.secrets["mongo"]["collection"]]
    except Exception as e:
        st.error(f"MongoDB Connection Error: {e}")
        return None

# --- 3. ROBUST DATA LOADER (FOR PAGE 2) ---
@st.cache_data(ttl=600)
def get_year_data(data_type, year):
    """
    Fetches raw data for ONE specific year.
    Does NOT aggregate on server (safer for mixed types).
    """
    # 1. Select Collection
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"
    
    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()

    # 2. Build Query (Fetch by Year String or Number)
    # This gets ~200k rows max, which loads in <5 seconds
    regex_pattern = f"^{year}"
    query = {
        "$or": [
            {"start_time": {"$regex": regex_pattern}}, # String dates (2022+)
            {"startTime": {"$regex": regex_pattern}},
            {"start_time": {"$type": "number"}},       # Numbers (2021 - fetch all numbers then filter)
            {"startTime": {"$type": "number"}}
        ]
    }
    
    # Only get necessary columns
    projection = {
        "price_area": 1, group_col: 1, 
        "start_time": 1, "startTime": 1, 
        "value": 1, "quantityKwh": 1, "_id": 0
    }

    # 3. Execute Query
    # Limit 500k protects against crashing memory
    cursor = coll.find(query, projection).limit(500000)
    data = list(cursor)
    df = pd.DataFrame(data)
    
    if df.empty: return df

    # 4. Cleanup
    if group_col in df.columns: df.rename(columns={group_col: 'group'}, inplace=True)
    df['group'] = df['group'].astype(str).fillna("Unknown")

    if "value" in df.columns: df.rename(columns={'value': 'mwh'}, inplace=True)
    elif "quantityKwh" in df.columns: df.rename(columns={'quantityKwh': 'mwh'}, inplace=True)

    # 5. Date Conversion (The Mixed Type Fix)
    date_col = "start_time" if "start_time" in df.columns else "startTime"
    
    df['temp'] = pd.to_numeric(df[date_col], errors='coerce')
    mask_num = df['temp'].notna()
    
    if mask_num.any():
        df.loc[mask_num, 'date'] = pd.to_datetime(df.loc[mask_num, 'temp'], unit='ms', utc=True)
    if (~mask_num).any():
        df.loc[~mask_num, 'date'] = pd.to_datetime(df.loc[~mask_num, date_col], utc=True, errors='coerce')
        
    df.drop(columns=['temp'], inplace=True)
    df['date'] = df['date'].dt.tz_convert("Europe/Oslo")

    # 6. Strict Year Filter (Removes any extra 2021 data if we grabbed too much)
    df = df[df['date'].dt.year == year]
    
    return df

# --- 4. MAP LOADER (Keep this, it works for Home Page) ---
@st.cache_data(ttl=3600)
def load_map_data(target_year, days_to_agg, data_type, selected_group):
    # ... (Keep the Aggregation logic from previous response here, or use the one below)
    # To be safe, I'll paste the ROBUST version here too:
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"

    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()

    # Regex Group Query
    query = {group_col: {"$regex": f"^{selected_group}$", "$options": "i"}}
    
    projection = {"price_area": 1, "start_time": 1, "startTime": 1, "value": 1, "quantityKwh": 1, "_id": 0}
    cursor = coll.find(query, projection).sort("_id", -1).limit(50000)
    df = pd.DataFrame(list(cursor))
    
    if df.empty: return df

    if "value" in df.columns: df.rename(columns={'value': 'val'}, inplace=True)
    elif "quantityKwh" in df.columns: df.rename(columns={'quantityKwh': 'val'}, inplace=True)
    if "price_area" in df.columns: df['price_area'] = df['price_area'].astype(str)

    date_col = "start_time" if "start_time" in df.columns else "startTime"
    df['temp'] = pd.to_numeric(df[date_col], errors='coerce')
    mask = df['temp'].notna()
    if mask.any(): df.loc[mask, 'date'] = pd.to_datetime(df.loc[mask, 'temp'], unit='ms', utc=True)
    if (~mask).any(): df.loc[~mask, 'date'] = pd.to_datetime(df.loc[~mask, date_col], utc=True, errors='coerce')
    df['date'] = df['date'].dt.tz_convert("Europe/Oslo")

    # Date Filter
    ref_date = pd.Timestamp(f"{target_year}-12-31", tz="Europe/Oslo")
    start_date = ref_date - pd.Timedelta(days=days_to_agg)
    mask = (df['date'].dt.year == target_year) & (df['date'] >= start_date)
    return df[mask]

# --- 5. API & GEOJSON ---
@st.cache_data(ttl=3600)
def fetch_weather_api(lat, lon, start_date, end_date):
    hourly_vars = ",".join(WEATHER_VARS)
    url = f"https://archive-api.open-meteo.com/v1/era5?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&hourly={hourly_vars}&timezone=Europe/Oslo"
    try:
        resp = requests.get(url, timeout=60); resp.raise_for_status(); js = resp.json()
        if "hourly" not in js: return pd.DataFrame()
        df = pd.DataFrame(js["hourly"])
        df["time"] = pd.to_datetime(df["time"])
        return df
    except: return pd.DataFrame()

@st.cache_data
def load_geojson():
    try:
        with open('elspot_areas.geojson', 'r') as f: return json.load(f)
    except: return None