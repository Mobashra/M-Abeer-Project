import streamlit as st
import plotly.express as px
from datetime import datetime
import utils # <--- Using shared utils

st.title("Elhub API Data (2021)")

# Load ONLY 2021 data to match your previous work
df = utils.load_elhub_data(year_filter=2021)

if df.empty:
    st.warning("No data found.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Production Share")
    price_areas = sorted(df['price_area'].unique())
    # Check if selected in Map page, otherwise default
    default_area = st.session_state.get("selected_price_area", price_areas[0])
    if default_area not in price_areas: default_area = price_areas[0]
    
    selected_area = st.radio("Select Price Area:", price_areas, index=price_areas.index(default_area))
    st.session_state["selected_price_area"] = selected_area # Sync
    
    filtered_area = df[df['price_area'] == selected_area]
    pie_data = filtered_area.groupby('production_group')['production_mwh'].sum().reset_index()
    fig1 = px.pie(pie_data, names='production_group', values='production_mwh')
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Monthly Trend")
    prod_groups = sorted(df['production_group'].unique())
    selected_groups = st.multiselect("Groups:", prod_groups, default=prod_groups)
    
    months = sorted(df['date'].dt.strftime('%B').unique())
    selected_month = st.selectbox("Month:", months)
    month_num = datetime.strptime(selected_month, '%B').month
    
    filtered_line = df[
        (df['price_area'] == selected_area) & 
        (df['production_group'].isin(selected_groups)) & 
        (df['date'].dt.month == month_num)
    ]
    
    if not filtered_line.empty:
        line_data = filtered_line.groupby(['date', 'production_group'])['production_mwh'].sum().reset_index()
        fig2 = px.line(line_data, x='date', y='production_mwh', color='production_group')
        st.plotly_chart(fig2, use_container_width=True)