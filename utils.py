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
    """
    Connects to MongoDB. 
    If collection_name is None, it uses the default 'collection' from secrets.
    """
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

# --- 3. OPTIMIZED LOADER (Year + Consumption Support) ---
@st.cache_data(ttl=3600)
def load_map_data(target_year, days_to_agg, data_type, selected_group):
    """
    Loads map data dynamically for Production OR Consumption.
    """
    # 1. Determine correct collection and column names
    if data_type == "Production":
        # Use default collection from secrets or specific name
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        # Use specific consumption key or default name
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"

    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()

    # 2. Build Query
    # Filter by Group (Regex for case-insensitivity)
    query = {group_col: {"$regex": f"^{selected_group}$", "$options": "i"}}
    
    # OPTIONAL: Filter by year string in MongoDB to speed it up
    # (Assumes your DB has ISO string dates like "2023-01-01...")
    start_str = f"{target_year}-01-01"
    end_str = f"{target_year}-12-31"
    # We add the date filter to the query. If DB has mixed types (int vs str), 
    # this might miss some rows, but our Pandas filter below catches them. 
    # It serves as a "pre-filter" for speed.
    query["$or"] = [
        {"start_time": {"$gte": start_str, "$lte": end_str}}, # Matches Strings
        {"startTime": {"$gte": start_str, "$lte": end_str}},  # Matches Strings
        {"start_time": {"$type": "number"}}, # Always fetch numbers (2021 data) just in case
        {"startTime": {"$type": "number"}}
    ]

    projection = {
        "price_area": 1, "start_time": 1, "startTime": 1, 
        "value": 1, "quantityKwh": 1, "_id": 0
    }
    
    # Fetch Data (Limit 50k is safe for one group/year)
    cursor = coll.find(query, projection).sort("_id", -1).limit(50000)
    df = pd.DataFrame(list(cursor))
    
    if df.empty: return df

    # 3. Standardize Columns
    if "price_area" in df.columns: df['price_area'] = df['price_area'].astype(str)
    if "value" in df.columns: df.rename(columns={'value': 'val'}, inplace=True)
    elif "quantityKwh" in df.columns: df.rename(columns={'quantityKwh': 'val'}, inplace=True)

    # 4. Date Conversion (Robust Mixed Types)
    date_col = "start_time" if "start_time" in df.columns else "startTime"
    
    df['temp_date'] = pd.to_numeric(df[date_col], errors='coerce')
    mask_num = df['temp_date'].notna()
    
    if mask_num.any():
        df.loc[mask_num, 'date'] = pd.to_datetime(df.loc[mask_num, 'temp_date'], unit='ms', utc=True)
    if (~mask_num).any():
        df.loc[~mask_num, 'date'] = pd.to_datetime(df.loc[~mask_num, date_col], utc=True, errors='coerce')

    df.drop(columns=['temp_date'], inplace=True)
    df['date'] = df['date'].dt.tz_convert("Europe/Oslo")

    # 5. Final Exact Filter (Year + Days Interval)
    # We calculate the "End Date" as Dec 31 of the selected year
    ref_date = pd.Timestamp(f"{target_year}-12-31", tz="Europe/Oslo")
    start_date = ref_date - pd.Timedelta(days=days_to_agg)
    
    # Keep data that is in the target year AND after the start date
    mask = (df['date'].dt.year == target_year) & (df['date'] >= start_date)
    
    return df[mask]

# --- 4. OTHER LOADERS ---
@st.cache_data(ttl=3600)
def load_elhub_data(year_filter=None):
    """Legacy loader for deep analysis pages."""
    coll = get_mongo_collection()
    if coll is None: return pd.DataFrame()
    
    # Basic fetch
    data = list(coll.find({}, {"_id": 0}))
    df = pd.DataFrame(data)
    if df.empty: return df

    # Cleanup
    if "production_group" in df.columns: df['production_group'] = df['production_group'].fillna("Unknown").astype(str)
    if "price_area" in df.columns: df['price_area'] = df['price_area'].fillna("Unknown").astype(str)
    
    # Date fix
    date_col = "start_time" if "start_time" in df.columns else "startTime"
    if date_col in df.columns:
        df['temp'] = pd.to_numeric(df[date_col], errors='coerce')
        mask = df['temp'].notna()
        if mask.any(): df.loc[mask, 'date'] = pd.to_datetime(df.loc[mask, 'temp'], unit='ms', utc=True)
        if (~mask).any(): df.loc[~mask, 'date'] = pd.to_datetime(df.loc[~mask, date_col], utc=True, errors='coerce')
        df['date'] = df['date'].dt.tz_convert("Europe/Oslo")
        df.drop(columns=['temp'], inplace=True)

    # Value fix
    if "value" in df.columns: df.rename(columns={'value': 'production_mwh'}, inplace=True)
    elif "quantityKwh" in df.columns: df.rename(columns={'quantityKwh': 'production_mwh'}, inplace=True)

    if year_filter:
        df = df[df["date"].dt.year == year_filter]
    return df

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