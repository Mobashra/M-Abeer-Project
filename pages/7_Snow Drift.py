import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import utils
import analysis_functions as af

st.set_page_config(page_title="Snow Drift", page_icon="❄️", layout="wide")
st.title("❄️ Snow Drift Physics (Tabler 2003)")


# --- SIDEBAR NAVIGATION GROUPS ---
st.sidebar.markdown("### 🗺️ Exploration")
# The pages 01, 02, 03 will appear here naturally due to sorting

if st.sidebar.checkbox("Show Advanced Modules", value=True):
    st.sidebar.markdown("### 🔍 Diagnostics")
    # Pages 04, 05, 06 fall here visually
    
    st.sidebar.markdown("### 🔮 Prediction")
    # Pages 07, 08 fall here visually


# --- STRICT REQUIREMENT: MAP DEPENDENCY ---
if "selected_coords" not in st.session_state:
    st.error("⛔ No location selected. Please go to the **Home Page** and select a location on the map.")
    st.stop()

coords = st.session_state["selected_coords"]
area = st.session_state.get("selected_price_area", "N/A")

st.success(f"Running model for **{area}** at Lat: {coords['lat']:.4f}, Lon: {coords['lon']:.4f}")

# --- PARAMS ---
with st.expander("⚙️ Physics Parameters", expanded=False):
    c1, c2 = st.columns(2)
    T = c1.number_input("Max Transport Dist (T)", value=3000)
    F = c2.number_input("Fetch Distance (F)", value=30000)

start_year = st.sidebar.number_input("Start Year", 2015, 2023, 2020)
end_year = st.sidebar.number_input("End Year", 2020, 2024, 2023)

if st.button("Calculate Drift"):
    # Fetch Data
    fetch_s = f"{start_year}-07-01"
    fetch_e = f"{end_year+1}-06-30"
    df = utils.fetch_weather_api(coords['lat'], coords['lon'], fetch_s, fetch_e)
    
    # Physics
    df = af.assign_hydro_year(df)
    df = af.calculate_snow_drift(df)
    
    # Aggregation
    results = []
    # Loop hydro years
    for y in range(start_year, end_year + 1):
        sub = df[df['hydro_year'] == y]
        if sub.empty: continue
        res = af.compute_seasonal_transport(sub, T, F)
        res['Season'] = f"{y}-{y+1}"
        results.append(res)
    
    res_df = pd.DataFrame(results)
    
    # Plotting
    tab1, tab2 = st.tabs(["Annual Drift", "Monthly Profile"])
    
    with tab1:
        st.subheader("Total Snow Transport per Season")
        fig = px.bar(res_df, x='Season', y='Qt_tonnes_m', color='Control_Type')
        st.plotly_chart(fig, use_container_width=True)
        
    with tab2:
        st.subheader("Monthly Accumulation Profile")
        # Logic to plot monthly drift for comparison
        df['Month'] = df['time'].dt.month_name()
        monthly = df.groupby(['hydro_year', 'Month'])['Qupot_hourly'].sum().reset_index()
        fig2 = px.line(monthly, x='Month', y='Qupot_hourly', color='hydro_year')
        st.plotly_chart(fig2, use_container_width=True)