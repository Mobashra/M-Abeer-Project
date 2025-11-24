import streamlit as st
import pandas as pd
import requests
import json
from pymongo import MongoClient
from datetime import timedelta

# --- 1. CONSTANTS ---
CITIES = {
    "NO1": {"city": "Oslo", "latitude": 59.9139, "longitude": 10.7522},
    "NO2": {"city": "Kristiansand", "latitude": 58.1467, "longitude": 7.9956},
    "NO3": {"city": "Trondheim", "latitude": 63.4305, "longitude": 10.3951},
    "NO4": {"city": "Tromsø", "latitude": 69.6492, "longitude": 18.9553},
    "NO5": {"city": "Bergen", "latitude": 60.3942, "longitude": 5.3221},
}

WEATHER_VARS = ["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]

# --- 2. DATABASE CONNECTION ---
@st.cache_resource
def get_mongo_collection():
    """Connects to MongoDB using secrets.toml"""
    try:
        client = MongoClient(st.secrets["mongo"]["uri"])
        db = client[st.secrets["mongo"]["database"]]
        return db[st.secrets["mongo"]["collection"]]
    except Exception as e:
        st.error(f"MongoDB Connection Error: {e}")
        return None

# --- 3. OPTIMIZED DATA LOADER (FOR MAP) ---
@st.cache_data(ttl=3600)
def load_map_data(days_back=30, selected_group="hydro"):
    """
    Optimized loader for the Home Page Map.
    Filters relative to the DATA's max date, not today's date.
    """
    coll = get_mongo_collection()
    if coll is None: return pd.DataFrame()

    # 1. Server-Side Filtering
    # Use a regex to be case-insensitive (matches "Hydro", "hydro", "HYDRO")
    query = {"production_group": {"$regex": f"^{selected_group}$", "$options": "i"}}
    
    projection = {
        "price_area": 1, "start_time": 1, "startTime": 1, 
        "value": 1, "quantityKwh": 1, "_id": 0
    }
    
    # 2. Fetch latest 100k rows for this group
    cursor = coll.find(query, projection).sort("_id", -1).limit(100000)
    data = list(cursor)
    
    df = pd.DataFrame(data)
    if df.empty: return df

    # 3. Standardize Columns
    if "price_area" in df.columns:
        df['price_area'] = df['price_area'].astype(str)
        
    if "value" in df.columns:
        df.rename(columns={'value': 'production_mwh'}, inplace=True)
    elif "quantityKwh" in df.columns:
        df.rename(columns={'quantityKwh': 'production_mwh'}, inplace=True)

    # 4. Robust Date Conversion
    date_col = "start_time" if "start_time" in df.columns else "startTime"
    
    df['temp_date'] = pd.to_numeric(df[date_col], errors='coerce')
    mask_num = df['temp_date'].notna()
    
    if mask_num.any():
        df.loc[mask_num, 'date'] = pd.to_datetime(df.loc[mask_num, 'temp_date'], unit='ms', utc=True)
    
    if (~mask_num).any():
        df.loc[~mask_num, 'date'] = pd.to_datetime(df.loc[~mask_num, date_col], utc=True, errors='coerce')

    df.drop(columns=['temp_date'], inplace=True)
    df['date'] = df['date'].dt.tz_convert("Europe/Oslo")

    # 5. FIXED TIME FILTER (Relative to Data, not Today)
    # Find the latest date actually present in this chunk of data
    max_data_date = df['date'].max()
    
    # Calculate cutoff relative to THAT date
    cutoff_date = max_data_date - pd.Timedelta(days=days_back)
    
    mask_time = df['date'] >= cutoff_date
    
    return df[mask_time]

# --- 4. FULL DATA LOADER (FOR DEEP ANALYSIS) ---
@st.cache_data(ttl=600)
def load_elhub_data(year_filter=None):
    """Loads ALL data. Use carefully!"""
    coll = get_mongo_collection()
    if coll is None: return pd.DataFrame()

    data = list(coll.find({}, {"_id": 0}))
    df = pd.DataFrame(data)

    if df.empty: return df

    if "production_group" in df.columns:
        df['production_group'] = df['production_group'].fillna("Unknown").astype(str)
    if "price_area" in df.columns:
        df['price_area'] = df['price_area'].fillna("Unknown").astype(str)
    
    date_col = "start_time" if "start_time" in df.columns else "startTime"
    
    if date_col in df.columns:
        # Fast mixed-type conversion
        df['temp_numeric'] = pd.to_numeric(df[date_col], errors='coerce')
        mask_num = df['temp_numeric'].notna()
        
        if mask_num.any():
            df.loc[mask_num, 'date'] = pd.to_datetime(df.loc[mask_num, 'temp_numeric'], unit='ms', utc=True)
        if (~mask_num).any():
            df.loc[~mask_num, 'date'] = pd.to_datetime(df.loc[~mask_num, date_col], utc=True, errors='coerce')
            
        df['date'] = df['date'].dt.tz_convert("Europe/Oslo")
        df.drop(columns=['temp_numeric'], inplace=True)

    if "value" in df.columns:
        df.rename(columns={'value': 'production_mwh'}, inplace=True)
    elif "quantityKwh" in df.columns:
        df.rename(columns={'quantityKwh': 'production_mwh'}, inplace=True)

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