import streamlit as st
import plotly.express as px
import pandas as pd
import utils

st.set_page_config(page_title="Energy Stats", layout="wide")

# 1. SAFETY & STYLING
utils.check_session_state()
utils.render_sidebar()

# 2. HEADER
st.title(f"📊 Energy Statistics: {st.session_state['selected_price_area']}")
st.markdown("Analyze historical production and consumption trends.")

# 3. CONTROLS (Dashboard Style)
with st.container():
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
    with c2:
        year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=2)
    with c3:
        st.info("💡 **Insight:** Toggle between Production and Consumption to see market balance.")

st.divider()

# 4. LOAD DATA
with st.spinner("Fetching energy data..."):
    df = utils.load_yearly_data(data_type, year)

if df.empty:
    st.error(f"No data found for {year}. Please check database connection.")
    st.stop()

# Filter by Global Area
current_area = st.session_state["selected_price_area"]
df_area = df[df['price_area'] == current_area].copy()

if df_area.empty:
    st.warning(f"No {data_type} data found for {current_area} in {year}.")
    st.stop()

# 5. VISUALIZATION
c_pie, c_line = st.columns([1, 2])

with c_pie:
    st.subheader("Market Share")
    pie_data = df_area.groupby('group')['mwh'].sum().reset_index()
    fig1 = px.pie(pie_data, values='mwh', names='group', hole=0.4, color_discrete_sequence=px.colors.qualitative.Prism)
    fig1.update_layout(legend=dict(orientation="h", y=-0.1))
    st.plotly_chart(fig1, use_container_width=True)

with c_line:
    st.subheader("Seasonal Trends")
    # Resample to Daily for cleaner lines
    if not pd.api.types.is_datetime64_any_dtype(df_area['date']):
        df_area['date'] = pd.to_datetime(df_area['date'])
        
    daily = df_area.set_index('date').groupby('group')['mwh'].resample('D').sum().reset_index()
    
    fig2 = px.line(daily, x='date', y='mwh', color='group', title=f"Daily {data_type} (MWh)")
    fig2.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig2, use_container_width=True)