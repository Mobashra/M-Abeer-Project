import streamlit as st
import plotly.express as px
import pandas as pd
import utils 

st.set_page_config(page_title="Elhub Data Explorer", layout="wide")
st.title("📊 Elhub Data Explorer")

if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

# --- CONTROLS ---
col1, col2 = st.columns(2)
with col1:
    data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
with col2:
    selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)

# --- LOAD DATA (AGGREGATED) ---
with st.spinner(f"Fetching daily stats for {selected_year}..."):
    # This is now super fast because it fetches only ~2000 rows
    df = utils.get_year_data(data_type, selected_year)

if df.empty:
    st.warning(f"No data found for **{data_type}** in **{selected_year}**.")
    st.stop()

# --- VISUALIZATION ---
col_left, col_right = st.columns(2)

# LEFT: PIE CHART (Shares)
with col_left:
    st.subheader(f"{data_type} Share")
    
    price_areas = sorted(df['price_area'].unique())
    curr = st.session_state["selected_price_area"]
    idx = price_areas.index(curr) if curr in price_areas else 0
    selected_area = st.selectbox("Price Area:", price_areas, index=idx)
    
    if selected_area != st.session_state["selected_price_area"]:
        st.session_state["selected_price_area"] = selected_area
        st.rerun()

    # Filter for selected area
    df_area = df[df['price_area'] == selected_area]
    
    # Aggregate the Daily sums into a Yearly Total for the Pie Chart
    pie_data = df_area.groupby('group')['daily_mwh'].sum().reset_index()
    
    fig1 = px.pie(pie_data, names='group', values='daily_mwh', hole=0.4,
                  title=f"Total {data_type} ({selected_area})")
    fig1.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig1, use_container_width=True)

# RIGHT: LINE CHART (Trends)
with col_right:
    st.subheader("Daily Trend")
    if not df_area.empty:
        all_groups = sorted(df_area['group'].unique())
        sel_groups = st.multiselect("Filter Groups:", all_groups, default=all_groups)
        
        if sel_groups:
            # The data is ALREADY Daily, so no resampling needed!
            df_line = df_area[df_area['group'].isin(sel_groups)].copy()
            
            fig2 = px.line(
                df_line, 
                x='date', 
                y='daily_mwh', 
                color='group', 
                title=f"Daily {data_type} over Time",
                labels={'daily_mwh': 'MWh', 'date': 'Date'}
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No data for this area.")

# --- RAW DATA ---
with st.expander("🔎 View Daily Data"):
    st.dataframe(df.head(200), use_container_width=True)