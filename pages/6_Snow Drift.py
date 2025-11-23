import streamlit as st
import plotly.express as px
import utils
import analysis_functions as af

st.title("❄️ Snow Drift Analysis")

if "selected_coords" not in st.session_state:
    st.warning("⚠️ Go to 'Map & Region Selector' page and click a location first.")
    st.stop()

coords = st.session_state["selected_coords"]
st.success(f"Analyzing Location: {coords['lat']:.4f}, {coords['lon']:.4f}")

# Fetch Data (Hydro Years)
start_year = st.number_input("Start Hydro Year", 2020, 2023, 2021)
df = utils.fetch_weather_api(coords['lat'], coords['lon'], f"{start_year}-07-01", f"{start_year+2}-06-30")

if not df.empty:
    df = af.assign_hydro_year(df)
    df = af.calculate_snow_drift(df)
    
    # Calculate Annual Stats
    years = df['hydro_year'].unique()
    results = []
    for y in years:
        sub = df[df['hydro_year'] == y]
        if not sub.empty:
            res = af.compute_seasonal_transport(sub)
            res['Year'] = y
            results.append(res)
    
    # Plot
    tab1, tab2 = st.tabs(["Annual Transport", "Wind Rose"])
    with tab1:
        st.dataframe(results)
        if results:
            fig = px.bar(results, x='Year', y='Qt_tonnes_m', color='Control', title="Annual Snow Transport")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        rose_data = af.get_wind_rose_data(df[df['Qupot_hourly'] > 0])
        if not rose_data.empty:
            fig = px.bar_polar(rose_data, r="Qupot_hourly", theta="sector_deg", title="Drift Direction")
            st.plotly_chart(fig, use_container_width=True)