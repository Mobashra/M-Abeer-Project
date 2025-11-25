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

# --- LOAD DATA ---
with st.spinner(f"Fetching daily stats for {selected_year}..."):
    # This returns data that is ALREADY grouped by Day (Fast!)
    df = utils.get_year_data(data_type, selected_year)

if df.empty:
    st.warning(f"No data found for **{data_type}** in **{selected_year}**.")
    st.stop()

# --- VISUALIZATION ---
col_left, col_right = st.columns(2)

# LEFT: PIE CHART (Shares)

with col_left:
    st.subheader(f"{data_type} Share")
    
    # Area Selector
    price_areas = sorted(df['price_area'].unique())
    curr = st.session_state["selected_price_area"]
    idx = price_areas.index(curr) if curr in price_areas else 0
    
    selected_area = st.selectbox("Price Area:", price_areas, index=idx)
    
    # Sync state
    if selected_area != st.session_state["selected_price_area"]:
        st.session_state["selected_price_area"] = selected_area
        st.rerun()

    # Filter for Area
    df_area = df[df['price_area'] == selected_area]
    
    # Aggregate
    pie_data = df_area.groupby('group')['mwh'].sum().reset_index()
    
    # Sort so the biggest slice starts at 12 o'clock (looks cleaner)
    pie_data = pie_data.sort_values('mwh', ascending=False)

    # Custom Pastel Colors (Matches your reference image vibe)
    custom_colors = ['#90C3C8', '#E8D68A', '#E39D86', '#CBB2E2', '#98C56D']

    fig1 = px.pie(
        pie_data, 
        names='group', 
        values='mwh', 
        # Remove 'hole' if you want a full pie like the image, or keep 0.4 for donut
        hole=0.0, 
        color_discrete_sequence=custom_colors
    )

    # Styling to match the image
    fig1.update_traces(
        textposition='auto',   # Puts small labels outside with lines
        textinfo='label+percent',
        insidetextorientation='horizontal',
        marker=dict(line=dict(color='#FFFFFF', width=2)) # White borders
    )
    
    # Layout adjustments for the labels
    fig1.update_layout(
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.05),
        margin=dict(t=30, b=30, l=20, r=20)
    )

    st.plotly_chart(fig1, use_container_width=True)

# RIGHT: LINE CHART (Trends)
with col_right:
    st.subheader("Daily Trend")
    if not df_area.empty:
        all_groups = sorted(df_area['group'].unique())
        sel_groups = st.multiselect("Filter Groups:", all_groups, default=all_groups)
        
        if sel_groups:
            # Filter for Group
            df_line = df_area[df_area['group'].isin(sel_groups)].copy()
            
            # Sort by date to ensure the line is smooth (Fixes "Zig-Zag" graphs)
            df_line = df_line.sort_values("date")
            
            # Plot directly (No resampling needed - it's already Daily!)
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