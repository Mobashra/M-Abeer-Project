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

# --- 3. MAP LOADER (Aggregation - FAST) ---
@st.cache_data(ttl=3600)
def load_map_data(target_year, days_to_agg, data_type, selected_group):
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"

    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()

    # Date Math
    end_date = datetime(target_year, 12, 31, 23, 59)
    start_date = end_date - timedelta(days=days_to_agg)
    start_str, end_str = start_date.isoformat(), end_date.isoformat()
    start_ts, end_ts = start_date.timestamp() * 1000, end_date.timestamp() * 1000

    pipeline = [
        {"$match": {group_col: {"$regex": f"^{selected_group}$", "$options": "i"}}},
        {"$match": {
            "$or": [
                {"start_time": {"$gte": start_str, "$lte": end_str}},
                {"startTime": {"$gte": start_str, "$lte": end_str}},
                {"start_time": {"$gte": start_ts, "$lte": end_ts}},
                {"startTime": {"$gte": start_ts, "$lte": end_ts}}
            ]
        }},
        {"$group": {
            "_id": "$price_area", 
            "val": {"$avg": "$value"},
            "val_alt": {"$avg": "$quantityKwh"}
        }}
    ]
    
    data = list(coll.aggregate(pipeline))
    df = pd.DataFrame(data)
    if df.empty: return df
    
    df['val'] = df['val'].fillna(df['val_alt'])
    df.rename(columns={'_id': 'price_area'}, inplace=True)
    df['price_area_map'] = df['price_area'].astype(str).str.replace("NO", "NO ")
    
    return df

# --- 4. PAGE 2 LOADER (Raw Fetch for 1 Year - ROBUST) ---
@st.cache_data(ttl=600)
def get_year_data(data_type, year):
    """
    Fetches detailed data for ONE year to populate charts.
    """
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"
    
    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()

    # Regex query for the year (Matches strings "2023-..." etc)
    regex_pattern = f"^{year}"
    query = {
        "$or": [
            {"start_time": {"$regex": regex_pattern}},
            {"startTime": {"$regex": regex_pattern}},
            {"start_time": {"$type": "number"}}, # Fetch numbers for 2021 filtering
            {"startTime": {"$type": "number"}}
        ]
    }
    
    # Fetch
    projection = {"price_area": 1, group_col: 1, "start_time": 1, "startTime": 1, "value": 1, "quantityKwh": 1, "_id": 0}
    cursor = coll.find(query, projection).limit(300000)
    df = pd.DataFrame(list(cursor))
    
    if df.empty: return df

    # Cleanup
    if group_col in df.columns: df.rename(columns={group_col: 'group'}, inplace=True)
    df['group'] = df['group'].astype(str).fillna("Unknown")
    
    if "value" in df.columns: df.rename(columns={'value': 'mwh'}, inplace=True)
    elif "quantityKwh" in df.columns: df.rename(columns={'quantityKwh': 'mwh'}, inplace=True)

    # Date Fix
    date_col = "start_time" if "start_time" in df.columns else "startTime"
    df['temp'] = pd.to_numeric(df[date_col], errors='coerce')
    mask_num = df['temp'].notna()
    
    if mask_num.any(): df.loc[mask_num, 'date'] = pd.to_datetime(df.loc[mask_num, 'temp'], unit='ms', utc=True)
    if (~mask_num).any(): df.loc[~mask_num, 'date'] = pd.to_datetime(df.loc[~mask_num, date_col], utc=True, errors='coerce')
        
    df['date'] = df['date'].dt.tz_convert("Europe/Oslo")
    
    # Strict Year Filter
    return df[df['date'].dt.year == year]

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