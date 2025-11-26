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

# --- 3. MAP LOADER (For Home.py) ---
@st.cache_data(ttl=3600)
def load_map_data(target_year, days_to_agg, data_type, selected_group):
    """
    Aggregates data on the server for the Map. Returns only ~5 rows.
    """
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"

    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()

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
    
    if not df.empty:
        df.rename(columns={'_id': 'price_area'}, inplace=True)
        df['price_area_map'] = df['price_area'].astype(str).str.replace("NO", "NO ")
        
    return df

# --- 4. AGGREGATED LOADER (For Page 2: Elhub Data) ---
@st.cache_data(ttl=3600)
def get_aggregated_year_data(data_type, year):
    """
    Returns two dataframes: pie_df (Total) and line_df (Daily).
    """
    if data_type == "Production":
        coll = get_mongo_collection(st.secrets["mongo"].get("collection"))
        group_col = "production_group"
    else:
        coll = get_mongo_collection(st.secrets["mongo"].get("collection_cons"))
        group_col = "consumption_group"

    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31, 23, 59, 59)
    match_stage = {"$match": {"start_time": {"$gte": start_date, "$lte": end_date}}}

    # Pie Pipeline
    pie_pipeline = [match_stage, {"$group": {"_id": f"${group_col}", "mwh": {"$sum": "$value"}}}]
    pie_data = list(coll.aggregate(pie_pipeline))
    pie_df = pd.DataFrame(pie_data)
    if not pie_df.empty: pie_df.rename(columns={'_id': 'group'}, inplace=True)

    # Line Pipeline
    line_pipeline = [
        match_stage,
        {"$project": {
            "group": f"${group_col}", "value": 1, "price_area": 1,
            "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$start_time", "timezone": "Europe/Oslo"}}
        }},
        {"$group": {"_id": {"area": "$price_area", "grp": "$group", "day": "$day"}, "daily_mwh": {"$sum": "$value"}}}
    ]
    line_data = list(coll.aggregate(line_pipeline))
    line_df = pd.DataFrame(line_data)
    
    if not line_df.empty:
        line_df['price_area'] = line_df['_id'].apply(lambda x: x['area'])
        line_df['group'] = line_df['_id'].apply(lambda x: x['grp'])
        line_df['date'] = pd.to_datetime(line_df['_id'].apply(lambda x: x['day']))
        line_df.drop(columns=['_id'], inplace=True)
        line_df.sort_values(['date'], inplace=True)

    return pie_df, line_df

# --- 5. RAW LOADER (For Page 3: STL) ---
@st.cache_data(ttl=3600)
def load_yearly_data(data_type, year):
    """
    Fetches RAW hourly data for deep analysis.
    """
    if data_type == "Production":
        coll = get_mongo_collection(st.secrets["mongo"].get("collection"))
        group_col = "production_group"
    else:
        coll = get_mongo_collection(st.secrets["mongo"].get("collection_cons"))
        group_col = "consumption_group"

    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31, 23, 59, 59)
    
    query = {"start_time": {"$gte": start_date, "$lte": end_date}}
    projection = {"price_area": 1, group_col: 1, "start_time": 1, "value": 1, "_id": 0}
    
    data = list(coll.find(query, projection).limit(300000))
    df = pd.DataFrame(data)
    
    if not df.empty:
        df.rename(columns={group_col: 'group', 'start_time': 'date', 'value': 'mwh'}, inplace=True)
        df['date'] = df['date'].dt.tz_convert("Europe/Oslo")
        df['group'] = df['group'].astype(str).fillna("Unknown")
        
    return df

# Backward compatibility alias (just in case)
get_year_data = load_yearly_data

# --- 6. API & GEOJSON ---
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