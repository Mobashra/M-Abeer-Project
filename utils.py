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

# --- 3. FAST LOADER (YEAR + TYPE) ---
@st.cache_data(ttl=600)
def load_yearly_data(data_type, year):
    """
    Loads ALL groups for a specific Year and Type (Prod/Cons).
    Optimized to fetch ~200k rows instead of 1 million.
    """
    # 1. Determine Collection
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"
    
    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()

    # 2. Build Query
    # Use Regex to filter by year string (Fastest for mixed types)
    regex_pattern = f"^{year}"
    query = {
        "$or": [
            {"start_time": {"$regex": regex_pattern}}, # String dates
            {"startTime": {"$regex": regex_pattern}},
            {"start_time": {"$type": "number"}},       # Numbers (2021)
            {"startTime": {"$type": "number"}}
        ]
    }
    
    projection = {
        "price_area": 1, group_col: 1, 
        "start_time": 1, "startTime": 1, 
        "value": 1, "quantityKwh": 1, "_id": 0
    }

    # Limit 300k is safe for one full year
    cursor = coll.find(query, projection).limit(300000)
    data = list(cursor)
    df = pd.DataFrame(data)
    
    if df.empty: return df

    # 3. Standardize Columns
    if group_col in df.columns:
        df.rename(columns={group_col: 'group'}, inplace=True)
    df['group'] = df['group'].astype(str).fillna("Unknown")

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

    # 5. Strict Year Filter
    df = df[df['date'].dt.year == year]
    
    return df

# --- 4. MAP LOADER ---
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

    end_date = datetime(target_year, 12, 31, 23, 59)
    start_date = end_date - timedelta(days=days_to_agg)
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    start_ts = start_date.timestamp() * 1000
    end_ts = end_date.timestamp() * 1000

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

# --- 5. LEGACY LOADER (Backup) ---
@st.cache_data(ttl=600)
def load_elhub_data(year_filter=None):
    coll = get_mongo_collection()
    if coll is None: return pd.DataFrame()
    data = list(coll.find({}, {"_id": 0}))
    df = pd.DataFrame(data)
    if df.empty: return df
    # (Basic cleanup omitted for brevity as we use specialized loaders now)
    return df

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


# --- ADD THIS TO utils.py ---

@st.cache_data(ttl=3600)
def aggregate_yearly_data(data_type, year):
    """
    Ultra-Fast: Asks MongoDB to group and sum data for the whole year.
    Returns:
      1. pie_df: Total MWh per Group (for Pie Chart)
      2. line_df: Daily MWh per Group (for Line Chart)
    """
    # 1. Setup Collection
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"
    
    coll = get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame(), pd.DataFrame()

    # 2. Define Time Range
    start_str = f"{year}-01-01"
    end_str = f"{year}-12-31"
    # Timestamps for 2021 numbers
    start_ts = datetime(year, 1, 1).timestamp() * 1000
    end_ts = datetime(year, 12, 31, 23, 59).timestamp() * 1000

    # 3. Match Stage (Filter Year)
    match_stage = {
        "$match": {
            "$or": [
                {"start_time": {"$gte": start_str, "$lte": end_str}},
                {"startTime": {"$gte": start_str, "$lte": end_str}},
                {"start_time": {"$gte": start_ts, "$lte": end_ts}},
                {"startTime": {"$gte": start_ts, "$lte": end_ts}}
            ]
        }
    }

    # 4. Pipeline for Pie Chart (Total per Group)
    pie_pipeline = [
        match_stage,
        {"$group": {
            "_id": f"${group_col}", 
            "total_mwh": {"$sum": "$value"},
            "total_mwh_alt": {"$sum": "$quantityKwh"}
        }}
    ]
    
    # 5. Pipeline for Line Chart (Daily per Group)
    # We project a 'day' string to group by
    line_pipeline = [
        match_stage,
        {"$project": {
            "group": f"${group_col}",
            "mwh": {"$ifNull": ["$value", "$quantityKwh"]}, # Handle both col names
            # Create a date string YYYY-MM-DD. 
            # Note: This simple substring works for ISO strings. 
            # For timestamps, it's trickier, so we might get raw rows for 2021 if needed.
            # But let's try the string approach first as it covers 2022-2024.
            "day_str": {"$substr": ["$start_time", 0, 10]} 
        }},
        {"$group": {
            "_id": {"day": "$day_str", "grp": "$group"},
            "daily_mwh": {"$sum": "$mwh"}
        }}
    ]

    # Run Queries
    pie_data = list(coll.aggregate(pie_pipeline))
    
    # For line data, aggregation is complex with mixed types. 
    # Fallback: Download raw data but ONLY 3 columns (Group, Time, Value)
    # This is still 10x faster than downloading everything.
    projection = {group_col: 1, "start_time": 1, "startTime": 1, "value": 1, "quantityKwh": 1, "_id": 0}
    raw_cursor = coll.find(match_stage["$match"], projection)
    raw_df = pd.DataFrame(list(raw_cursor))

    # Process Pie Data
    pie_df = pd.DataFrame(pie_data)
    if not pie_df.empty:
        pie_df['mwh'] = pie_df['total_mwh'].fillna(0) + pie_df['total_mwh_alt'].fillna(0)
        pie_df.rename(columns={'_id': 'group'}, inplace=True)

    # Process Line Data (Raw Pandas)
    if not raw_df.empty:
        # Standardize Cols
        if group_col in raw_df.columns: raw_df.rename(columns={group_col: 'group'}, inplace=True)
        if "value" in raw_df.columns: raw_df.rename(columns={'value': 'mwh'}, inplace=True)
        elif "quantityKwh" in raw_df.columns: raw_df.rename(columns={'quantityKwh': 'mwh'}, inplace=True)
        
        # Fix Dates
        date_c = "start_time" if "start_time" in raw_df.columns else "startTime"
        raw_df['date'] = pd.to_numeric(raw_df[date_c], errors='coerce')
        mask = raw_df['date'].notna()
        
        # Convert
        if mask.any(): raw_df.loc[mask, 'date'] = pd.to_datetime(raw_df.loc[mask, 'date'], unit='ms', utc=True)
        if (~mask).any(): raw_df.loc[~mask, 'date'] = pd.to_datetime(raw_df.loc[~mask, date_c], utc=True, errors='coerce')
        
        raw_df['date'] = raw_df['date'].dt.tz_convert("Europe/Oslo")
        
        # Group by Day
        line_df = raw_df.groupby([pd.Grouper(key='date', freq='D'), 'group'])['mwh'].sum().reset_index()
    else:
        line_df = pd.DataFrame()

    return pie_df, line_df