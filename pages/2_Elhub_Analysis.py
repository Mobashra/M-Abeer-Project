import streamlit as st
import plotly.express as px
import pandas as pd
import utils 

st.set_page_config(page_title="Elhub Data Explorer", layout="wide")
st.title("📊 Elhub Data Explorer")

# --- 1. SAFETY DEFAULT ---
# Ensures the app doesn't crash if you refresh this page directly
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

# --- 2. CONTROLS (Top Bar) ---
col1, col2 = st.columns(2)
with col1:
    # Toggle: Production vs Consumption
    data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
with col2:
    # Select any year from your clean database
    selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)

# --- 3. LOAD DATA (Fast & Clean) ---
# This uses the new 'load_yearly_data' function from utils.py
# It fetches ~200k rows in <2 seconds because dates are indexed.
with st.spinner(f"Loading {data_type} data for {selected_year}..."):
    df = utils.load_yearly_data(data_type, selected_year)

if df.empty:
    st.warning(f"No data found for **{data_type}** in **{selected_year}**.")
    st.stop()

# --- 4. VISUALIZATION ---
col_left, col_right = st.columns(2)

# --- LEFT COLUMN: PIE CHART (Market Share) ---
with col_left:
    st.subheader(f"{data_type} Share")
    
    # Area Selector (Defaults to Home Page selection)
    price_areas = sorted(df['price_area'].unique())
    curr = st.session_state["selected_price_area"]
    # Safety check: if current selection isn't in list, default to first option
    idx = price_areas.index(curr) if curr in price_areas else 0
    
    selected_area = st.selectbox("Price Area:", price_areas, index=idx)
    
    # Sync state if changed here
    if selected_area != st.session_state["selected_price_area"]:
        st.session_state["selected_price_area"] = selected_area
        st.rerun()

    # Filter for Pie Chart
    df_area = df[df['price_area'] == selected_area]
    
    # Aggregate totals
    pie_data = df_area.groupby('group')['mwh'].sum().reset_index()
    
    fig1 = px.pie(pie_data, names='group', values='mwh', hole=0.4,
                  title=f"Total {data_type} ({selected_area})")
    fig1.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig1, use_container_width=True)

# --- RIGHT COLUMN: LINE CHART (Trends) ---
with col_right:
    st.subheader("Daily Trend")
    
    if not df_area.empty:
        # Group Filter
        all_groups = sorted(df_area['group'].unique())
        sel_groups = st.multiselect("Filter Groups:", all_groups, default=all_groups)
        
        if sel_groups:
            # Filter by selected groups
            df_line = df_area[df_area['group'].isin(sel_groups)].copy()
            
            # Set index for resampling
            df_line.set_index('date', inplace=True)
            
            # Resample to Daily (D) 
            # Plotting 8760 hourly points is slow/messy. Daily (365 points) is clean.
            line_data = df_line.groupby('group')['mwh'].resample('D').sum().reset_index()
            
            fig2 = px.line(
                line_data, 
                x='date', 
                y='mwh', 
                color='group', 
                labels={'mwh': 'MWh', 'date': 'Date'},
                title=f"Daily {data_type} over Time"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Select at least one group to see the chart.")
    else:
        st.info("No data available for this area.")

# --- 5. DATA PEEK ---
with st.expander("🔎 View Raw Data"):
    st.dataframe(df.head(200), use_container_width=True)