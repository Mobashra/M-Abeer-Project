import streamlit as st
import pandas as pd
import requests
import json
from pymongo import MongoClient

# --- CONFIGURATION ---
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
    """Connects to MongoDB using secrets.toml"""
    try:
        client = MongoClient(st.secrets["mongo"]["uri"])
        db = client[st.secrets["mongo"]["database"]]
        return db[st.secrets["mongo"]["collection"]]
    except Exception as e:
        st.error(f"MongoDB Connection Error: {e}")
        return None

# --- DATA LOADERS ---
@st.cache_data(ttl=600)
def load_elhub_data(year_filter=None):
    """
    Loads production data. 
    If year_filter is set (e.g., 2021), it keeps only that year to match your old logic.
    """
    coll = get_mongo_collection()
    if coll is None: return pd.DataFrame()

    # Fetch data (excluding _id to save memory)
    data = list(coll.find({}, {"_id": 0}))
    df = pd.DataFrame(data)

    if df.empty: return df

    # Cleanup types
    if "production_group" in df.columns:
        df['production_group'] = df['production_group'].fillna("Unknown").astype(str)
    if "price_area" in df.columns:
        df['price_area'] = df['price_area'].fillna("Unknown").astype(str)
    
    # Handle Dates (UTC -> Oslo)
    if "start_time" in df.columns:
        df['date'] = pd.to_datetime(df['start_time'], unit='ms').dt.tz_localize("UTC").dt.tz_convert("Europe/Oslo")
    elif "startTime" in df.columns:
        df['date'] = pd.to_datetime(df['startTime'], utc=True).dt.tz_convert("Europe/Oslo")

    # Standardize value column name
    if "value" in df.columns and "production_mwh" not in df.columns:
        df.rename(columns={'value': 'production_mwh'}, inplace=True)
    elif "quantityKwh" in df.columns:
        df.rename(columns={'quantityKwh': 'production_mwh'}, inplace=True)

    # Optional Year Filter (To preserve your 2021 specific pages)
    if year_filter:
        df = df[df["date"].dt.year == year_filter]

    return df

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
        st.error("File 'elspot_areas.geojson' not found. Please download it from NVE.")
        return None