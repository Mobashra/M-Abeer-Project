import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import utils
import analysis_functions as af
import numpy as np

st.set_page_config(page_title="Snow Drift Analysis", layout="wide")
st.title("❄️ Snow Drift Analysis (Tabler 2003)")

# --- 1. CHECK DATA REQUIREMENTS ---
if "selected_coords" not in st.session_state:
    st.warning("⚠️ No location selected! Please go to the **Map Overview** page and click a location first.")
    st.stop()

coords = st.session_state["selected_coords"]
area = st.session_state.get("selected_price_area", "Unknown Location")

st.info(f"**Analysis Location:** {area} ({coords['lat']:.4f}, {coords['lon']:.4f})")

# --- 2. CONFIGURATION (Like your screenshot) ---
with st.expander("⚙️ Configuration & Parameters", expanded=True):
    with st.form("snow_params"):
        st.markdown("#### Model Parameters")
        c1, c2, c3 = st.columns(3)
        with c1:
            T = st.number_input("Max Transport Dist (T) [m]", value=3000, step=100, help="Distance snow can be transported")
        with c2:
            F = st.number_input("Fetch Distance (F) [m]", value=30000, step=1000, help="Upwind distance available for snow pick-up")
        with c3:
            theta = st.number_input("Relocation Coeff (theta)", value=0.5, step=0.1)
            
        st.markdown("#### Time Range (Hydro Years)")
        c4, c5 = st.columns(2)
        with c4:
            start_year = st.number_input("Start Year", 2015, 2023, 2021)
        with c5:
            end_year = st.number_input("End Year", min_value=start_year, max_value=2024, value=2023)
            
        submit = st.form_submit_button("Update Analysis")

# Default fetch if form not clicked yet, or update on click
# Hydro Year 2021 = July 1, 2021 -> June 30, 2022
fetch_start = f"{start_year}-07-01"
fetch_end = f"{end_year + 1}-06-30"

# --- 3. FETCH DATA ---
with st.spinner(f"Fetching weather data ({fetch_start} to {fetch_end})..."):
    df = utils.fetch_weather_api(coords['lat'], coords['lon'], fetch_start, fetch_end)

if df.empty:
    st.error("No weather data found for this period/location.")
    st.stop()

# --- 4. CALCULATIONS ---
# Apply Physics
df = af.assign_hydro_year(df)
df = af.calculate_snow_drift(df)

# Aggregate per Hydro Year
years = range(start_year, end_year + 1)
results = []
sector_list = []
monthly_data = []

for y in years:
    # Filter for specific Hydro Year
    sub = df[df['hydro_year'] == y].copy()
    if sub.empty: continue
    
    # A. Annual Totals (Tabler Logic)
    res = af.compute_seasonal_transport(sub, T, F, theta)
    res['Season'] = f"{y}-{y+1}" # Format: "2021-2022"
    
    # B. Fence Heights
    res['Wyoming (m)'] = af.compute_fence_height(res['Qt_kg_m'], "Wyoming")
    res['Slat-Wire (m)'] = af.compute_fence_height(res['Qt_kg_m'], "Slat-and-wire")
    res['Solid (m)'] = af.compute_fence_height(res['Qt_kg_m'], "Solid")
    
    results.append(res)
    
    # C. Wind Rose Data (Only when snow is drifting)
    drift_events = sub[sub['Qupot_hourly'] > 0]
    if not drift_events.empty:
        sector_list.append(af.get_wind_rose_data(drift_events))
        
    # D. Monthly Breakdown (Bonus)
    sub['Month'] = sub['time'].dt.strftime('%Y-%m')
    mon_agg = sub.groupby('Month')['Qupot_hourly'].sum().reset_index()
    mon_agg['Season'] = f"{y}-{y+1}"
    monthly_data.append(mon_agg)

# --- 5. VISUALIZATION ---
if not results:
    st.warning("No snow drift detected in this period (Temp likely > 1°C).")
    st.stop()

df_res = pd.DataFrame(results)

# TABS
tab1, tab2 = st.tabs(["📊 Annual Overview", "📈 Monthly Breakdown"])

# --- TAB 1: ANNUAL + ROSE ---
with tab1:
    c_left, c_right = st.columns([3, 2])
    
    with c_left:
        st.subheader("Annual Snow Transport (Qt)")
        fig_annual = px.bar(
            df_res, x='Season', y='Qt_tonnes_m', color='Control_Type',
            title="Total Snow Transport per Season",
            labels={'Qt_tonnes_m': 'Transport (Tonnes/m)'},
            text_auto='.1f',
            color_discrete_map={"Wind Limited": "#636EFA", "Snowfall Limited": "#EF553B"}
        )
        st.plotly_chart(fig_annual, use_container_width=True)
        
        # Fence Table
        st.markdown("#### Required Fence Heights")
        cols_show = ['Season', 'Qt_tonnes_m', 'Wyoming (m)', 'Slat-Wire (m)', 'Solid (m)']
        st.dataframe(
            df_res[cols_show].style.format("{:.2f}", subset=cols_show[1:]),
            use_container_width=True,
            hide_index=True
        )

    with c_right:
        st.subheader("Directional Transport")
        if sector_list:
            # Combine all years and average
            all_sectors = pd.concat(sector_list)
            avg_rose = all_sectors.groupby('sector_deg')['Qupot_hourly'].mean().reset_index()
            
            # Polar Bar Chart (Wind Rose)
            fig_rose = go.Figure(go.Barpolar(
                r=avg_rose['Qupot_hourly'],
                theta=avg_rose['sector_deg'],
                marker_color='blue',
                marker_line_color='black',
                marker_line_width=1,
                opacity=0.8
            ))
            
            fig_rose.update_layout(
                template='plotly_white',
                title="Avg Drift Potential (kg/m)",
                polar=dict(
                    angularaxis=dict(direction="clockwise", rotation=90),
                    radialaxis=dict(showticklabels=True)
                )
            )
            st.plotly_chart(fig_rose, use_container_width=True)
        else:
            st.info("No drift events to plot.")

# --- TAB 2: MONTHLY (BONUS) ---
with tab2:
    st.subheader("Monthly Snow Accumulation")
    if monthly_data:
        df_mon = pd.concat(monthly_data)
        fig_mon = px.area(
            df_mon, x='Month', y='Qupot_hourly', color='Season',
            title="Monthly Potential Transport (Q_pot)",
            labels={'Qupot_hourly': 'Transport (kg/m)'}
        )
        st.plotly_chart(fig_mon, use_container_width=True)