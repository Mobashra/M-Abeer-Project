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

# --- 3. ULTRA-FAST MAP LOADER (AGGREGATION) ---
@st.cache_data(ttl=3600)
def load_map_data(target_year, days_to_agg, data_type, selected_group):
    """
    Uses MongoDB Aggregation to calculate averages on the server.
    Returns 5 rows instead of 100,000. Instant load time.
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

    # 2. Calculate Date Range
    # We need to handle both Integers (2021) and Strings (2022+) in the query
    end_date = datetime(target_year, 12, 31, 23, 59)
    start_date = end_date - timedelta(days=days_to_agg)
    
    # Formats for String-based data
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    
    # Formats for Number-based data (milliseconds)
    start_ts = start_date.timestamp() * 1000
    end_ts = end_date.timestamp() * 1000

    # 3. The Aggregation Pipeline (Server-Side Math)
    pipeline = [
        # A. Filter by Group (Case Insensitive)
        {"$match": {group_col: {"$regex": f"^{selected_group}$", "$options": "i"}}},
        
        # B. Filter by Date (Handles BOTH types)
        {"$match": {
            "$or": [
                {"start_time": {"$gte": start_str, "$lte": end_str}}, # Strings
                {"startTime": {"$gte": start_str, "$lte": end_str}},  # Strings
                {"start_time": {"$gte": start_ts, "$lte": end_ts}},   # Numbers
                {"startTime": {"$gte": start_ts, "$lte": end_ts}}    # Numbers
            ]
        }},
        
        # C. Group & Average (The magic step that shrinks data)
        {"$group": {
            "_id": "$price_area", 
            "val": {"$avg": "$value"},          # Average of 'value'
            "val_alt": {"$avg": "$quantityKwh"} # Average of 'quantityKwh'
        }}
    ]
    
    # Run Query
    data = list(coll.aggregate(pipeline))
    df = pd.DataFrame(data)
    
    if df.empty: return df
    
    # Cleanup
    df['val'] = df['val'].fillna(df['val_alt'])
    df.rename(columns={'_id': 'price_area'}, inplace=True)
    
    # Fix "NO1" -> "NO 1" for map matching
    df['price_area_map'] = df['price_area'].astype(str).str.replace("NO", "NO ")
    
    return df

# --- 4. DEEP DIVE LOADER (FOR OTHER PAGES) ---
@st.cache_data(ttl=600)
def load_elhub_data(year_filter=None):
    """
    Legacy loader for detailed analysis pages.
    Includes mixed-type fixes for dates.
    """
    coll = get_mongo_collection()
    if coll is None: return pd.DataFrame()

    # Optimization: If year is provided, filter somewhat on server
    query = {}
    if year_filter:
        # Simple regex for string dates (works for 2022+)
        # For 2021 numbers, we just load and filter in Pandas
        pass 

    data = list(coll.find(query, {"_id": 0}))
    df = pd.DataFrame(data)
    if df.empty: return df

    # Cleanup
    if "production_group" in df.columns: df['production_group'] = df['production_group'].fillna("Unknown").astype(str)
    if "price_area" in df.columns: df['price_area'] = df['price_area'].fillna("Unknown").astype(str)
    
    # Fix Mixed Dates
    date_col = "start_time" if "start_time" in df.columns else "startTime"
    if date_col in df.columns:
        df['temp'] = pd.to_numeric(df[date_col], errors='coerce')
        mask = df['temp'].notna()
        if mask.any(): df.loc[mask, 'date'] = pd.to_datetime(df.loc[mask, 'temp'], unit='ms', utc=True)
        if (~mask).any(): df.loc[~mask, 'date'] = pd.to_datetime(df.loc[~mask, date_col], utc=True, errors='coerce')
        df['date'] = df['date'].dt.tz_convert("Europe/Oslo")
        df.drop(columns=['temp'], inplace=True)

    # Fix Value Names
    if "value" in df.columns: df.rename(columns={'value': 'production_mwh'}, inplace=True)
    elif "quantityKwh" in df.columns: df.rename(columns={'quantityKwh': 'production_mwh'}, inplace=True)

    if year_filter:
        df = df[df["date"].dt.year == year_filter]
        
    return df

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


# --- ADD THIS TO utils.py ---

@st.cache_data(ttl=600)
def load_yearly_data(data_type, year):
    """
    Loads data for a specific Year and Type (Prod/Cons).
    Fetches ALL groups for that year (needed for Pie Charts).
    """
    # 1. Determine Collection & Column Names
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"
    
    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()

    # 2. Build Query for Specific Year (Server-Side Filtering)
    # Regex is the safest way to catch both String dates ("2022-01...") 
    # and prevent downloading other years.
    regex_pattern = f"^{year}"
    
    # We accept either String format (2022+) or Numbers (2021)
    # This query gets roughly 200k rows (5 areas * 5 groups * 8760 hours)
    # This is manageable for Streamlit.
    query = {
        "$or": [
            {"start_time": {"$regex": regex_pattern}}, # String dates
            {"startTime": {"$regex": regex_pattern}},
            # For 2021 numbers, we fetch based on numeric range if year is 2021
            {"start_time": {"$type": "number"}}, 
            {"startTime": {"$type": "number"}}
        ]
    }
    
    # Optimization: Only fetch columns we need
    projection = {
        "price_area": 1, group_col: 1, 
        "start_time": 1, "startTime": 1, 
        "value": 1, "quantityKwh": 1, "_id": 0
    }

    # Limit 300k is safe for a full year of hourly data
    cursor = coll.find(query, projection).limit(300000)
    data = list(cursor)
    df = pd.DataFrame(data)
    
    if df.empty: return df

    # 3. Standardize Columns (So the page code is clean)
    # Rename specific group col to generic 'group'
    if group_col in df.columns:
        df.rename(columns={group_col: 'group'}, inplace=True)
    df['group'] = df['group'].astype(str).fillna("Unknown")

    # Standardize Value
    if "value" in df.columns: df.rename(columns={'value': 'mwh'}, inplace=True)
    elif "quantityKwh" in df.columns: df.rename(columns={'quantityKwh': 'mwh'}, inplace=True)

    # 4. Standardize Date
    date_col = "start_time" if "start_time" in df.columns else "startTime"
    
    df['temp'] = pd.to_numeric(df[date_col], errors='coerce')
    mask_num = df['temp'].notna()
    
    if mask_num.any():
        df.loc[mask_num, 'date'] = pd.to_datetime(df.loc[mask_num, 'temp'], unit='ms', utc=True)
    if (~mask_num).any():
        df.loc[~mask_num, 'date'] = pd.to_datetime(df.loc[~mask_num, date_col], utc=True, errors='coerce')
        
    df.drop(columns=['temp'], inplace=True)
    df['date'] = df['date'].dt.tz_convert("Europe/Oslo")

    # 5. Strict Year Filter (Cleanup any extra numeric data)
    df = df[df['date'].dt.year == year]
    
    return df