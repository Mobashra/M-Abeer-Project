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

# --- ACTIVE AREA CONTEXT ---
current_context_area = st.session_state.get("selected_price_area", "NO1")
st.info(f"📍 **Currently Viewing:** Price Area **{current_context_area}**")

# 3. GLOBAL SETTINGS (Data Source & Year)
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
    st.subheader("1. Regional Distribution")
    
    # A. Radio Button for Price Area
    available_areas = sorted(df['price_area'].unique())
    try:
        default_index = available_areas.index(st.session_state.get("selected_price_area", "NO1"))
    except ValueError:
        default_index = 0
        
    selected_area_radio = st.radio(
        "Select Price Area",
        options=available_areas,
        index=default_index,
        horizontal=True,
        key="area_radio_selector"
    )
    
    # Sync session state
    st.session_state["selected_price_area"] = selected_area_radio

    # Filter data
    df_area = df[df['price_area'] == selected_area_radio].copy()

    # B. Pie Chart (Left Aligned Styling)
    if not df_area.empty:
        pie_data = df_area.groupby('group')['mwh'].sum().reset_index().sort_values('mwh', ascending=False)
        
        fig_pie = px.pie(
            pie_data, 
            values='mwh', 
            names='group', 
            hole=0.4, 
            color_discrete_sequence=px.colors.qualitative.Prism,
            title=f"Total {data_type} Mix ({year})"
        )
        
        fig_pie.update_layout(legend=dict(orientation="h", y=0.1))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning("No data for this area.")


# --- RIGHT COLUMN: Group/Month Selection & Line Chart ---
with col_right:
    st.subheader("2. Seasonal Details")
    
    if not df_area.empty:
        # A. Pills for Groups
        all_groups = sorted(df_area['group'].unique())
        
        selected_groups = st.pills(
            f"Select {data_type} Groups",
            options=all_groups,
            selection_mode="multi",
            default=all_groups 
        )
        
        # B. Month Range Slider (THE FIX: st.select_slider)
        months_map = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 
                      7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
        
        # We use select_slider because it supports 'options' and 'format_func'
        start_month, end_month = st.select_slider(
            "Select Month Range",
            options=list(months_map.keys()), # The numbers 1-12
            value=(1, 12),                   # Default Range
            format_func=lambda x: months_map[x] # Show names (Jan, Feb)
        )

        # C. Filter Logic
        if selected_groups:
            df_filtered = df_area[df_area['group'].isin(selected_groups)].copy()
            
            # Filter by Month Range
            df_filtered = df_filtered[
                (df_filtered['date'].dt.month >= start_month) & 
                (df_filtered['date'].dt.month <= end_month)
            ]
            
            if not df_filtered.empty:
                # Dynamic Title
                if start_month == end_month:
                    date_range_str = months_map[start_month]
                else:
                    date_range_str = f"{months_map[start_month]} - {months_map[end_month]}"

                # D. Line Chart
                fig_line = px.line(
                    df_filtered, 
                    x='date', 
                    y='mwh', 
                    color='group',
                    title=f"{date_range_str} Trends in {selected_area_radio}",
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_line.update_layout(
                    hovermode="x unified", 
                    legend=dict(orientation="h", y=1.1),
                    yaxis_title="MWh"
                )
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info(f"No data available for the selected range.")
        else:
            st.warning("Please select at least one group using the pills above.")


# 6. RAW DATA
with st.expander("🔎 View Raw Data"):
    st.dataframe(df_area.head(10), use_container_width=True)


# ======================================================
# 7. DOCUMENTATION (EXPANDER)
# ======================================================
with st.expander("📄 Data Source & Documentation"):
    st.markdown("""
    **Data Source:**
    * **Elhub API:** [https://api.elhub.no](https://api.elhub.no)
    
    **Notes:**
    * **Pie Chart:** Represents the total accumulated energy for the selected *Year*.
    * **Line Chart:** Shows high-resolution trends for the specific *Month Range* selected.
    * **Price Areas:** NO1 (Oslo), NO2 (Kristiansand), NO3 (Trondheim), NO4 (Tromsø), NO5 (Bergen).
    """)