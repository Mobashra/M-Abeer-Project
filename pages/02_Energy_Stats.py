import streamlit as st
import plotly.express as px
import pandas as pd
import utils
from datetime import datetime

st.set_page_config(page_title="Energy Stats", layout="wide")

# 1. SAFETY & STYLING
utils.check_session_state()
utils.render_sidebar()

# 2. HEADER
st.title("📊 Energy Statistics")

# 3. GLOBAL SETTINGS (Data Source & Year)
# We keep these at the top so the data can be loaded first
with st.container():
    c1, c2 = st.columns(2)
    with c1:
        data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
    with c2:
        year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)

st.divider()

# 4. LOAD DATA
with st.spinner(f"Fetching {data_type} data for {year}..."):
    df = utils.load_yearly_data(data_type, year)

if df.empty:
    st.error(f"No data found for {year}. Please check database connection.")
    st.stop()

# Ensure date column is datetime objects for filtering
if not pd.api.types.is_datetime64_any_dtype(df['date']):
    df['date'] = pd.to_datetime(df['date'])

# ======================================================
# 5. SPLIT VIEW (LEFT & RIGHT)
# ======================================================
col_left, col_right = st.columns(2, gap="medium")

# --- LEFT COLUMN: Area Selection & Pie Chart ---
with col_left:
    st.subheader("Regional Distribution")
    
    # A. Radio Button for Price Area
    # We default to the session state area, but allow changing it here
    available_areas = sorted(df['price_area'].unique())
    try:
        default_index = available_areas.index(st.session_state.get("selected_price_area", "NO1"))
    except ValueError:
        default_index = 0
        
    selected_area_radio = st.radio(
        "Select Price Area",
        options=available_areas,
        index=default_index,
        horizontal=True
    )

    # Filter data for this area
    df_area = df[df['price_area'] == selected_area_radio].copy()

    # B. Pie Chart
    if not df_area.empty:
        # Aggregate totals for the whole year (or you can filter by month here too if preferred)
        pie_data = df_area.groupby('group')['mwh'].sum().reset_index().sort_values('mwh', ascending=False)
        
        fig_pie = px.pie(
            pie_data, 
            values='mwh', 
            names='group', 
            hole=0.4, 
            color_discrete_sequence=px.colors.qualitative.Prism,
            title=f"{data_type} Mix in {selected_area_radio} ({year})"
        )
        fig_pie.update_layout(legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning("No data for this area.")


# --- RIGHT COLUMN: Group/Month Selection & Line Chart ---
with col_right:
    st.subheader("Seasonal Details")
    
    if not df_area.empty:
        # A. Pills for Production/Consumption Groups
        all_groups = sorted(df_area['group'].unique())
        
        selected_groups = st.pills(
            f"Select {data_type} Groups",
            options=all_groups,
            selection_mode="multi",
            default=all_groups # Default to selecting all
        )
        
        # B. Month Selector
        # Create a list of months present in the data
        # (Using 1-12 integers for logic, formatting them as Names for display)
        months_map = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 
                      7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}
        
        current_month = datetime.now().month
        
        selected_month_num = st.selectbox(
            "Select Month",
            options=months_map.keys(),
            format_func=lambda x: months_map[x],
            index=0 # Default to January
        )

        # C. Filter Logic
        if selected_groups:
            # Filter by Group
            df_filtered = df_area[df_area['group'].isin(selected_groups)].copy()
            
            # Filter by Month
            df_filtered = df_filtered[df_filtered['date'].dt.month == selected_month_num]
            
            if not df_filtered.empty:
                # D. Line Chart
                # Resample to Hourly or Daily depending on preference. 
                # Since we are looking at a single month, Hourly resolution is usually good.
                # If it's too noisy, you can use .resample('D')
                
                fig_line = px.line(
                    df_filtered, 
                    x='date', 
                    y='mwh', 
                    color='group',
                    title=f"{months_map[selected_month_num]} Trends in {selected_area_radio}",
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_line.update_layout(
                    hovermode="x unified", 
                    legend=dict(orientation="h", y=1.1),
                    yaxis_title="MWh"
                )
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info(f"No data available for {months_map[selected_month_num]}.")
        else:
            st.warning("Please select at least one group using the pills above.")


# 6. RAW DATA
with st.expander("🔎 View Raw Data"):
    st.dataframe(df_area.head(10), use_container_width=True)


# ======================================================
# 6. DOCUMENTATION (EXPANDER)
# ======================================================
with st.expander("📄 Data Source & Documentation"):
    st.markdown("""
    **Data Source:**
    * **Elhub API:** [https://api.elhub.no](https://api.elhub.no)
    
    **Notes:**
    * **Pie Chart:** Represents the total accumulated energy for the selected *Year*.
    * **Line Chart:** Shows high-resolution trends for the specific *Month* selected.
    * **Price Areas:** NO1 (Oslo), NO2 (Kristiansand), NO3 (Trondheim), NO4 (Tromsø), NO5 (Bergen).
    """)