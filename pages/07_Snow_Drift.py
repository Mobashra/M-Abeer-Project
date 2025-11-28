import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import utils
import analysis_functions as af
import numpy as np

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Snow Drift Analysis", layout="wide")

# 1. SAFETY & STYLING
utils.check_session_state()
utils.render_sidebar()

st.title("❄️ Snow Drift Analysis (Tabler 2003)")

# 2. CONTEXT
coords = st.session_state["selected_coords"]
area = st.session_state["selected_price_area"]

st.info(f"**Analysis Location:** {area} (Lat: {coords['lat']:.4f}, Lon: {coords['lon']:.4f})")

# 3. CONFIGURATION
with st.container():
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.markdown("#### 📅 Time Selection")
        # User chooses range of "Hydro Years"
        start_year = st.number_input("Start Year", 2015, 2023, 2021, help="Year the winter starts (e.g. 2021 = July 2021 to June 2022)")
        end_year = st.number_input("End Year", min_value=start_year, max_value=2024, value=2023)
        
    with c2:
        st.markdown("#### ⚙️ Model Parameters")
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            T = st.number_input("Max Transport (T)", value=3000, step=100, help="Max transport distance in meters")
        with c_p2:
            F = st.number_input("Fetch Distance (F)", value=30000, step=1000, help="Upwind distance snow can drift from")
        with c_p3:
            theta = st.number_input("Relocation (θ)", value=0.5, step=0.1, help="Relocation coefficient")

    if st.button("🚀 Run Analysis", type="primary"):
        # Define Hydro Year Range: July 1st (Start Year) -> June 30th (End Year + 1)
        fetch_start = f"{start_year}-07-01"
        fetch_end = f"{end_year + 1}-06-30"
        
        with st.spinner(f"Fetching weather data ({fetch_start} to {fetch_end})..."):
            df = utils.fetch_weather_api(coords['lat'], coords['lon'], fetch_start, fetch_end)

        if df.empty:
            st.error("No weather data found for this period/location.")
            st.stop()

        # --- 4. CALCULATIONS ---
        # Apply Physics
        df = af.assign_hydro_year(df)
        df = af.calculate_snow_drift(df)

        annual_results = []
        monthly_results = []
        sector_list = []

        # Loop through each requested Hydro Year
        years_range = range(start_year, end_year + 1)

        for y in years_range:
            # Filter for specific Hydro Year (July 1 - June 30)
            sub = df[df['hydro_year'] == y].copy()
            if sub.empty: continue
           
            # A. Annual Totals
            res = af.compute_seasonal_transport(sub, T, F, theta)
            res['Season'] = f"{y}-{y+1}" # Label as "2021-2022"
            
            # B. Fence Heights (Tabler 2003)
            res['Wyoming (m)'] = af.compute_fence_height(res['Qt_kg_m'], "Wyoming")
            res['Slat-Wire (m)'] = af.compute_fence_height(res['Qt_kg_m'], "Slat-and-wire")
            res['Solid (m)'] = af.compute_fence_height(res['Qt_kg_m'], "Solid")
           
            annual_results.append(res)
           
            # C. Wind Rose Data (Drift Events Only)
            drift_events = sub[sub['Qupot_hourly'] > 0]
            if not drift_events.empty:
                sector_list.append(af.get_wind_rose_data(drift_events))
            
            # D. Monthly Breakdown (BONUS)
            # We sort months hydro-logically: July(7) -> Dec(12) -> Jan(1) -> June(6)
            sub['MonthNum'] = sub['time'].dt.month
            hydro_order = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]
            
            for m in hydro_order:
                m_sub = sub[sub['MonthNum'] == m]
                if m_sub.empty: continue
                
                # Calculate transport just for this month
                m_res = af.compute_seasonal_transport(m_sub, T, F, theta)
                
                monthly_results.append({
                    "Season": f"{y}-{y+1}",
                    "MonthNum": m,
                    "Month": pd.to_datetime(f"2000-{m}-01").strftime('%b'), # Get name 'Jan', 'Feb'
                    "Qt (tonnes/m)": m_res['Qt_tonnes_m']
                })

        if not annual_results:
            st.warning("No snow drift detected in this period (Temperatures might be too high).")
            st.stop()

        df_res = pd.DataFrame(annual_results)

        # --- 5. VISUALIZATION ---
        tab1, tab2 = st.tabs(["📊 Annual Overview", "📈 Monthly Analysis (Bonus)"])

        # --- TAB 1: ANNUAL ---
        with tab1:
            c_left, c_right = st.columns([2, 1])
           
            with c_left:
                st.subheader("Total Snow Transport (Qt)")
                fig_annual = px.bar(
                    df_res, x='Season', y='Qt_tonnes_m', color='Control_Type',
                    title="Seasonal Snow Transport",
                    labels={'Qt_tonnes_m': 'Transport (Tonnes/m)'},
                    text_auto='.1f',
                    color_discrete_map={"Wind Limited": "#636EFA", "Snowfall Limited": "#EF553B"}
                )
                st.plotly_chart(fig_annual, use_container_width=True)
                
                st.markdown("#### 🚧 Recommended Fence Heights")
                cols_show = ['Season', 'Qt_tonnes_m', 'Wyoming (m)', 'Slat-Wire (m)', 'Solid (m)']
                st.dataframe(
                    df_res[cols_show].style.format("{:.2f}", subset=cols_show[1:]),
                    use_container_width=True,
                    hide_index=True
                )

            with c_right:
                st.subheader("🌬️ Drift Wind Rose")
                if sector_list:
                    # Average the wind rose sectors across all selected years
                    all_sectors = pd.concat(sector_list)
                    avg_rose = all_sectors.groupby('sector_deg')['Qupot_hourly'].mean().reset_index()
                   
                    fig_rose = go.Figure(go.Barpolar(
                        r=avg_rose['Qupot_hourly'],
                        theta=avg_rose['sector_deg'],
                        marker_color='blue',
                        marker_line_color='black',
                        marker_line_width=1,
                        opacity=0.7
                    ))
                   
                    fig_rose.update_layout(
                        template='plotly_white',
                        title="Avg Drift Potential (kg/m)",
                        polar=dict(angularaxis=dict(direction="clockwise", rotation=90))
                    )
                    st.plotly_chart(fig_rose, use_container_width=True)
                else:
                    st.info("No significant drift wind events.")

        # --- TAB 2: MONTHLY (BONUS) ---
        with tab2:
            st.subheader("Seasonal Progression")
            st.caption("Compare how snow accumulation builds up month-by-month across different years.")
           
            if monthly_results:
                df_mon = pd.DataFrame(monthly_results)
               
                # Sort months correctly for the X-axis (July -> June)
                month_order = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
                df_mon['Month'] = pd.Categorical(df_mon['Month'], categories=month_order, ordered=True)
                df_mon = df_mon.sort_values(['Season', 'Month'])
               
                fig_mon = px.line(
                    df_mon,
                    x='Month',
                    y='Qt (tonnes/m)',
                    color='Season',
                    markers=True,
                    symbol='Season',
                    title="Monthly Snow Transport Comparison",
                    labels={'Qt (tonnes/m)': 'Transport (Tonnes/m)'}
                )
               
                fig_mon.update_layout(
                    xaxis_title=None,
                    hovermode="x unified",
                    template="plotly_white",
                    legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
                )
               
                st.plotly_chart(fig_mon, use_container_width=True)
            else:
                st.info("No monthly data available.")