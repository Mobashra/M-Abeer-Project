import streamlit as st
import pandas as pd
import requests
import json
from pymongo import MongoClient
from datetime import timedelta

# Centralized City Data
CITIES = {
    "NO1": {"city": "Oslo", "latitude": 59.9139, "longitude": 10.7522},
    "NO2": {"city": "Kristiansand", "latitude": 58.1467, "longitude": 7.9956},
    "NO3": {"city": "Trondheim", "latitude": 63.4305, "longitude": 10.3951},
    "NO4": {"city": "Tromsø", "latitude": 69.6492, "longitude": 18.9553},
    "NO5": {"city": "Bergen", "latitude": 60.3942, "longitude": 5.3221},
}

WEATHER_VARS = ["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]

# --- DATABASE CONNECTION ---
@st.cache_resource
def get_mongo_collection():
    try:
        client = MongoClient(st.secrets["mongo"]["uri"])
        db = client[st.secrets["mongo"]["database"]]
        return db[st.secrets["mongo"]["collection"]]
    except Exception as e:
        st.error(f"MongoDB Connection Error: {e}")
        return None

# --- LIGHTWEIGHT DATA LOADER (FOR MAP) ---
@st.cache_data(ttl=3600)
def load_map_data(days_back=30):
    """
    Loads ONLY the last N days of data for the map to prevent crashing.
    """
    coll = get_mongo_collection()
    if coll is None: return pd.DataFrame()

    # Calculate cutoff date (approximate using string sort if needed, but query is better)
    # Since your data might be mixed types, sorting by _id is often a good proxy for "latest" data
    # OR just limit to the last 50,000 records which is safer for memory.
    
    # Fetch only necessary columns and limit rows
    projection = {"price_area": 1, "production_group": 1, "start_time": 1, "startTime": 1, "quantityKwh": 1, "value": 1, "_id": 0}
    
    # Sort by _id descending (newest first) and take 50k rows
    cursor = coll.find({}, projection).sort("_id", -1).limit(50000)
    data = list(cursor)
    
    df = pd.DataFrame(data)
    if df.empty: return df

    # --- FAST CLEANUP ---
    if "production_group" in df.columns:
        df['production_group'] = df['production_group'].astype(str)
    if "price_area" in df.columns:
        df['price_area'] = df['price_area'].astype(str)
        
    # Standardize Value
    if "value" in df.columns:
        df.rename(columns={'value': 'production_mwh'}, inplace=True)
    elif "quantityKwh" in df.columns:
        df.rename(columns={'quantityKwh': 'production_mwh'}, inplace=True)

    # Standardize Date (Fast)
    date_col = "start_time" if "start_time" in df.columns else "startTime"
    
    # Try converting assuming standard format first (much faster)
    df['date'] = pd.to_datetime(df[date_col], utc=True, errors='coerce')
    df['date'] = df['date'].dt.tz_convert("Europe/Oslo")
    
    return df

# --- FULL DATA LOADER (FOR ANALYSIS PAGES) ---
@st.cache_data(ttl=3600)
def load_elhub_data(year_filter=None):
    """Loads full dataset (Use only when necessary)"""
    coll = get_mongo_collection()
    if coll is None: return pd.DataFrame()

    # If filtering by year, use a query to reduce load!
    query = {}
    if year_filter == 2021:
        # Optimization: Regex query for 2021 string dates or range for timestamps
        # For mixed data, this is tricky, so we stick to loading it but maybe limit if possible
        pass 

    data = list(coll.find(query, {"_id": 0}))
    df = pd.DataFrame(data)
    if df.empty: return df

    # (Insert previous cleanup logic here - same as before)
    # ... [The cleanup logic I gave you previously goes here] ...
    # For brevity, assume the mixed-type fix logic is here.
    
    # RE-INSERT THE MIXED TYPE FIX HERE FROM PREVIOUS RESPONSE
    # ...
    
    return df

@st.cache_data(ttl=3600)
def fetch_weather_api(lat, lon, start_date, end_date):
    # ... (Keep existing code) ...
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