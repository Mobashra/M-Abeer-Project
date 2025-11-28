import streamlit as st
import plotly.express as px
import pandas as pd
import utils

st.set_page_config(page_title="Energy Stats", layout="wide")

# 1. SAFETY & STYLING
utils.check_session_state()
utils.render_sidebar()

# 2. HEADER & CONTEXT INFO
st.title("📊 Energy Statistics")

# --- NEW: Info at the top ---
current_area = st.session_state["selected_price_area"]
coords = st.session_state["selected_coords"]

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    c1.metric("📍 Active Region", current_area)
    c2.metric("🌐 Latitude", f"{coords['lat']:.4f}")
    c3.metric("🌐 Longitude", f"{coords['lon']:.4f}")

# 3. CONTROLS
with st.container():
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
    with c2:
        year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=2)
    with c3:
        st.info(f"Analyzing **{data_type}** data for **{year}**.")

st.divider()

# 4. LOAD DATA
with st.spinner("Fetching energy data..."):
    df = utils.load_yearly_data(data_type, year)

if df.empty:
    st.error(f"No data found for {year}. Please check database connection.")
    st.stop()

# Filter by Global Area
df_area = df[df['price_area'] == current_area].copy()

if df_area.empty:
    st.warning(f"No {data_type} data found for {current_area} in {year}.")
    st.stop()

# 5. VISUALIZATION
c_pie, c_line = st.columns([1, 2])

# --- LEFT: Modern Pie Chart ---
with c_pie:
    st.subheader("Market Share")
    
    # Aggregation
    pie_data = df_area.groupby('group')['mwh'].sum().reset_index().sort_values('mwh', ascending=False)
    
    fig1 = px.pie(
        pie_data, 
        values='mwh', 
        names='group', 
        hole=0.4, # Donut style (Your preference)
        color_discrete_sequence=px.colors.qualitative.Prism,
        title=f"Total {data_type} Mix"
    )
    fig1.update_layout(legend=dict(orientation="h", y=-0.1))
    st.plotly_chart(fig1, use_container_width=True)

# --- RIGHT: Line Chart with Filter ---
with c_line:
    st.subheader("Seasonal Trends")
    
    # Group Filter
    all_groups = sorted(df_area['group'].unique())
    sel_groups = st.multiselect("Filter Groups:", all_groups, default=all_groups)
    
    if sel_groups:
        df_line = df_area[df_area['group'].isin(sel_groups)].copy()
        
        # Safe Date Conversion
        if not pd.api.types.is_datetime64_any_dtype(df_line['date']):
            df_line['date'] = pd.to_datetime(df_line['date'])
            
        # Resample to Daily for cleaner chart
        daily = df_line.set_index('date').groupby('group')['mwh'].resample('D').sum().reset_index()
        
        fig2 = px.line(
            daily, 
            x='date', 
            y='mwh', 
            color='group', 
            title=f"Daily {data_type} (MWh)",
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig2.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Select groups above to view trends.")

# 6. RAW DATA
with st.expander("🔎 View Raw Data"):
    st.dataframe(df_area.head(500), use_container_width=True)