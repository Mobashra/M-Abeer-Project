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
with st.spinner(f"Fetching data for {selected_year}..."):
    df = utils.get_year_data(data_type, selected_year)

if df.empty:
    st.warning(f"No data found for **{data_type}** in **{selected_year}**.")
    st.stop()

# --- 1. SMART COLUMN DETECTION ---
# This fixes the KeyError! It checks which column exists in your data.
if 'daily_mwh' in df.columns:
    val_col = 'daily_mwh' # Found the Fast Aggregated Data
elif 'mwh' in df.columns:
    val_col = 'mwh'       # Found the Raw Data
else:
    st.error(f"Data Error: Could not find value column. Available columns: {df.columns.tolist()}")
    st.stop()

# --- VISUALIZATION ---
col_left, col_right = st.columns(2)

# LEFT: PIE CHART

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

    # Filter & Aggregate
    df_area = df[df['price_area'] == selected_area]
    
    # Group by 'group' and sum the 'daily_mwh' (or 'mwh' if raw)
    # We detect the column name dynamically to be safe
    val_col = 'daily_mwh' if 'daily_mwh' in df_area.columns else 'mwh'
    pie_data = df_area.groupby('group')[val_col].sum().reset_index()
    
    # --- STYLING ---
    fig1 = px.pie(
        pie_data, 
        names='group', 
        values=val_col,
        title=f"Total {data_type} in {selected_area} ({selected_year})",
        color_discrete_sequence=px.colors.qualitative.Pastel  # Your requested pastel colors
    )

    fig1.update_traces(
        textposition='auto',       # Puts large labels inside, small ones outside
        textinfo='percent+label',  # Shows "Wind 2.8%"
        pull=[0.05] * len(pie_data), # Explodes slices slightly
        marker=dict(line=dict(color='#000000', width=1)), # Thin black border
        insidetextorientation='horizontal' # Keeps text readable inside the pie
    )
    
    # Layout adjustments to fix the label bunching
    fig1.update_layout(
        title=dict(x=0.5, xanchor='center'),
        font=dict(size=14),
        showlegend=True,
        # Add margin so the "outside" labels have room and don't get cut off
        margin=dict(t=80, b=50, l=50, r=50),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="right", x=1.2) # Move legend out of the way
    )

    st.plotly_chart(fig1, use_container_width=True)

# RIGHT: LINE CHART
with col_right:
    st.subheader("Daily Trend")
    if not df_area.empty:
        all_groups = sorted(df_area['group'].unique())
        sel_groups = st.multiselect("Filter Groups:", all_groups, default=all_groups)
        
        if sel_groups:
            df_line = df_area[df_area['group'].isin(sel_groups)].copy()
            df_line.set_index('date', inplace=True)
            df_line.sort_index(inplace=True) # Ensure time order
            
            # Resample to Daily (Works for both Hourly and Daily input)
            line_data = df_line.groupby('group')[val_col].resample('D').sum().reset_index()
            
            fig2 = px.line(
                line_data, 
                x='date', 
                y=val_col, 
                color='group', 
                title=f"Daily {data_type} over Time",
                labels={val_col: 'MWh', 'date': 'Date'}
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No data for this area.")

# --- RAW DATA ---
with st.expander("🔎 View Data"):
    st.dataframe(df.head(200), use_container_width=True)