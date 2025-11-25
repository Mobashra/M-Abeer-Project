import streamlit as st
import plotly.express as px
import pandas as pd
from pymongo import MongoClient
import utils 

st.set_page_config(page_title="Elhub Data Explorer", layout="wide")
st.title("📊 Elhub Data Explorer")

# --- 1. SESSION STATE SAFETY ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

# --- 2. CUSTOM DATA LOADER (Page Specific) ---
# We define a specific loader here to handle the Year/Type logic efficiently
@st.cache_data(ttl=600)
def load_filtered_data(data_type, year):
    """
    Loads data for a specific Year and Type (Prod/Cons).
    Renames group columns to 'group' for consistent plotting.
    """
    # 1. Determine Collection
    if data_type == "Production":
        coll_name = st.secrets["mongo"].get("collection", "production_mba_hour")
        group_col = "production_group"
    else:
        coll_name = st.secrets["mongo"].get("collection_cons", "consumption_mba_hour")
        group_col = "consumption_group"
    
    coll = utils.get_mongo_collection(coll_name)
    if coll is None: return pd.DataFrame()

    # 2. Build Query for Specific Year
    # We use a Regex on the start_time string to filter by year (Fastest method for mixed types)
    # Matches "2022-..." or similar.
    regex_pattern = f"^{year}"
    query = {
        "$or": [
            {"start_time": {"$regex": regex_pattern}}, # String dates (2022+)
            {"startTime": {"$regex": regex_pattern}},
            # For 2021 numbers, we fetch all and filter in Pandas (safer for mixed types)
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

    data = list(coll.find(query, projection))
    df = pd.DataFrame(data)
    if df.empty: return df

    # 3. Standardize Group Name
    # Rename specific group col to generic 'group'
    if group_col in df.columns:
        df.rename(columns={group_col: 'group'}, inplace=True)
    df['group'] = df['group'].astype(str).fillna("Unknown")

    # 4. Standardize Value
    if "value" in df.columns: df.rename(columns={'value': 'mwh'}, inplace=True)
    elif "quantityKwh" in df.columns: df.rename(columns={'quantityKwh': 'mwh'}, inplace=True)

    # 5. Standardize Date
    date_col = "start_time" if "start_time" in df.columns else "startTime"
    
    df['temp'] = pd.to_numeric(df[date_col], errors='coerce')
    mask_num = df['temp'].notna()
    
    if mask_num.any():
        df.loc[mask_num, 'date'] = pd.to_datetime(df.loc[mask_num, 'temp'], unit='ms', utc=True)
    if (~mask_num).any():
        df.loc[~mask_num, 'date'] = pd.to_datetime(df.loc[~mask_num, date_col], utc=True, errors='coerce')
        
    df.drop(columns=['temp'], inplace=True)
    df['date'] = df['date'].dt.tz_convert("Europe/Oslo")

    # 6. Final Year Filter (To clean up the Number-based fetch)
    df = df[df['date'].dt.year == year]
    
    return df

# --- 3. CONTROLS ---
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)

with col_ctrl1:
    data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)

with col_ctrl2:
    selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)

# Load Data based on selection
with st.spinner(f"Loading {data_type} data for {selected_year}..."):
    df = load_filtered_data(data_type, selected_year)

if df.empty:
    st.warning(f"No data found for **{data_type}** in **{selected_year}**.")
    st.stop()

# --- 4. VISUALIZATION LAYOUT ---
col1, col2 = st.columns(2)

# --- LEFT: PIE CHART (Shares) ---
with col1:
    st.subheader(f"{data_type} Share")
    
    # Area Selector
    price_areas = sorted(df['price_area'].unique())
    curr = st.session_state["selected_price_area"]
    if curr not in price_areas: curr = price_areas[0]
    
    selected_area = st.selectbox("Price Area:", price_areas, index=price_areas.index(curr))
    
    # Sync state
    if selected_area != st.session_state["selected_price_area"]:
        st.session_state["selected_price_area"] = selected_area
        st.rerun()

    # Filter
    df_area = df[df['price_area'] == selected_area]
    
    # Aggregate
    pie_data = df_area.groupby('group')['mwh'].sum().reset_index()
    
    # Plot
    fig1 = px.pie(pie_data, names='group', values='mwh', hole=0.4,
                  title=f"Total {data_type} by Group ({selected_area})")
    fig1.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig1, use_container_width=True)

# --- RIGHT: LINE CHART (Trends) ---
with col2:
    st.subheader(f"Monthly Trend ({selected_year})")
    
    groups = sorted(df['group'].unique())
    selected_groups = st.multiselect("Filter Groups:", groups, default=groups)
    
    if selected_groups:
        # Filter by groups and area
        df_line = df_area[df_area['group'].isin(selected_groups)].copy()
        
        # Resample to Daily or Monthly to make the chart readable
        # (Plotting 8760 hours is too slow and messy)
        df_line.set_index('date', inplace=True)
        # Resample by Day ('D') or Week ('W')
        df_resampled = df_line.groupby('group')['mwh'].resample('D').sum().reset_index()
        
        fig2 = px.line(
            df_resampled, 
            x='date', 
            y='mwh', 
            color='group',
            title=f"Daily {data_type} Trend",
            labels={'mwh': 'MWh', 'date': 'Date'}
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Select at least one group to see the trend.")

# --- FOOTER ---
with st.expander("View Raw Data"):
    st.dataframe(df.head(100), use_container_width=True)