import streamlit as st
import plotly.express as px
import pandas as pd
import utils
import analysis_functions as af

st.set_page_config(page_title="Snow Drift", layout="wide")

utils.check_session_state()
utils.render_sidebar()

st.title("❄️ Snow Drift Accumulation")
coords = st.session_state["selected_coords"]
st.success(f"Modeling snow transport for: Lat {coords['lat']:.2f}, Lon {coords['lon']:.2f}")

c1, c2, c3 = st.columns([1, 1, 2])
with c1: start_y = st.number_input("Start Year", 2015, 2023, 2020)
with c2: end_y = st.number_input("End Year", 2016, 2024, 2023)
with c3: st.info("Calculates Tabler (2003) transport potential.")

if st.button("Run Simulation", type="primary"):
    with st.spinner("Simulating physics..."):
        df = utils.fetch_weather_api(coords['lat'], coords['lon'], f"{start_y}-07-01", f"{end_y+1}-06-30")
        
        if not df.empty:
            df = af.assign_hydro_year(df)
            df = af.calculate_snow_drift(df)
            
            results = []
            for y in range(start_y, end_y + 1):
                sub = df[df['hydro_year'] == y]
                if not sub.empty:
                    res = af.compute_seasonal_transport(sub)
                    res['Year'] = y
                    results.append(res)
            
            if results:
                res_df = pd.DataFrame(results)
                fig = px.bar(res_df, x='Year', y='Qt_tonnes_m', color='Control_Type', title="Seasonal Snow Transport")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No snow drift events.")