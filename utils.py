import streamlit as st
import pandas as pd
import requests
import json
from pymongo import MongoClient
from datetime import datetime, timedelta

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
    Filters by group on the server to avoid downloading 1 million rows.
    """
    coll = get_mongo_collection()
    if coll is None: return pd.DataFrame()

    # 1. Server-Side Filtering
    # We only fetch the specific group requested (e.g., "wind").
    # This reduces data volume by ~80% immediately.
    query = {"production_group": selected_group}
    
    # We only fetch necessary columns (No need for everything)
    projection = {
        "price_area": 1, "start_time": 1, "startTime": 1, 
        "value": 1, "quantityKwh": 1, "_id": 0
    }
    
    # 2. Limit Result Size
    # 365 days * 24 hours * 5 areas = ~43,800 rows.
    # We fetch the last 100,000 rows to be safe for a full year history.
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

    # 4. Robust Date Conversion (Handles Mixed Types)
    date_col = "start_time" if "start_time" in df.columns else "startTime"
    
    # Fast conversion: coerce errors turns strings to NaT, numbers to NaT depending on format
    # First try numeric (ms)
    df['temp_date'] = pd.to_numeric(df[date_col], errors='coerce')
    
    mask_num = df['temp_numeric_date'] = df['temp_date'].notna()
    
    # Convert numeric rows
    if mask_num.any():
        df.loc[mask_num, 'date'] = pd.to_datetime(df.loc[mask_num, 'temp_date'], unit='ms', utc=True)
    
    # Convert string rows
    if (~mask_num).any():
        df.loc[~mask_num, 'date'] = pd.to_datetime(df.loc[~mask_num, date_col], utc=True, errors='coerce')

    df.drop(columns=['temp_date'], inplace=True)
    df['date'] = df['date'].dt.tz_convert("Europe/Oslo")

    # 5. Final Time Filter
    cutoff_date = pd.Timestamp.now(tz="Europe/Oslo") - pd.Timedelta(days=days_back)
    mask_time = df['date'] >= cutoff_date
    
    return df[mask_time]

# --- 4. FULL DATA LOADER (LEGACY / DEEP ANALYSIS) ---
@st.cache_data(ttl=600)
def load_elhub_data(year_filter=None):
    """
    Loads ALL data. Use carefully! Ideally use load_map_data where possible.
    """
    coll = get_mongo_collection()
    if coll is None: return pd.DataFrame()

    # Fetch data excluding _id
    data = list(coll.find({}, {"_id": 0}))
    df = pd.DataFrame(data)

    if df.empty: return df

    # Cleanup types
    if "production_group" in df.columns:
        df['production_group'] = df['production_group'].fillna("Unknown").astype(str)
    if "price_area" in df.columns:
        df['price_area'] = df['price_area'].fillna("Unknown").astype(str)
    
    # --- ROBUST DATE HANDLING ---
    date_col = "start_time" if "start_time" in df.columns else "startTime"
    
    if date_col in df.columns:
        is_numeric = pd.to_numeric(df[date_col], errors='coerce').notna()
        if (~is_numeric).any():
            df.loc[~is_numeric, 'date'] = pd.to_datetime(df.loc[~is_numeric, date_col], utc=True, errors='coerce')
        if is_numeric.any():
            df.loc[is_numeric, 'date'] = pd.to_datetime(df.loc[is_numeric, date_col], unit='ms', utc=True)
        df['date'] = df['date'].dt.tz_convert("Europe/Oslo")

    # Standardize value column name
    if "value" in df.columns and "production_mwh" not in df.columns:
        df.rename(columns={'value': 'production_mwh'}, inplace=True)
    elif "quantityKwh" in df.columns:
        df.rename(columns={'quantityKwh': 'production_mwh'}, inplace=True)

    # Optional Year Filter
    if year_filter:
        df = df[df["date"].dt.year == year_filter]

    return df

# --- 5. API & GEOJSON ---
@st.cache_data(ttl=3600)
def fetch_weather_api(lat, lon, start_date, end_date):
    """Fetches ERA5 weather data."""
    hourly_vars = ",".join(WEATHER_VARS)
    url = (
        f"https://archive-api.open-meteo.com/v1/era5"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&hourly={hourly_vars}&timezone=Europe/Oslo"
    )
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        js = resp.json()
        if "hourly" not in js: return pd.DataFrame()
        
        df = pd.DataFrame(js["hourly"])
        df["time"] = pd.to_datetime(df["time"])
        return df
    except Exception as e:
        st.error(f"Weather API Error: {e}")
        return pd.DataFrame()

@st.cache_data
def load_geojson():
    """Loads the NVE Map Data"""
    try:
        with open('elspot_areas.geojson', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Try json extension just in case
        try:
            with open('elspot_areas.json', 'r') as f:
                return json.load(f)
        except:
            st.error("File 'elspot_areas.geojson' not found. Please download it from NVE.")
            return None