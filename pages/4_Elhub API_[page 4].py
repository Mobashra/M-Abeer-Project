import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import plotly.express as px

# -------------------------------
# Page setup
# -------------------------------
st.set_page_config(page_title="New Data", layout="wide")
st.title("Elhub API Data")

# -------------------------------
# MongoDB connection with caching
# -------------------------------
@st.cache_resource
def get_mongo_collection():
    client = MongoClient(st.secrets["mongo"]["uri"])
    db = client[st.secrets["mongo"]["database"]]
    collection = db[st.secrets["mongo"]["collection"]]
    return collection

collection = get_mongo_collection()

# -------------------------------
# Load and preprocess data with caching
# -------------------------------
@st.cache_data(ttl=600)
def load_data():
    data = list(collection.find())
    df = pd.DataFrame(data)
    if df.empty:
        return df

    # Clean columns
    df['production_group'] = df['production_group'].fillna("Unknown").astype(str)
    df['price_area'] = df['price_area'].fillna("Unknown").astype(str)

    # Convert timestamps
    df['date'] = pd.to_datetime(df['start_time'], unit='ms')

    # Rename for clarity
    df.rename(columns={'value': 'production_mwh'}, inplace=True)
    return df

df = load_data()

if df.empty:
    st.warning("No data found in the MongoDB collection.")
    st.stop()

# -------------------------------
# Layout with two columns
# -------------------------------
col1, col2 = st.columns(2)

# Price area + Pie chart
with col1:
    st.subheader("Production Share by Price Area")

    price_areas = sorted(df['price_area'].unique())
    selected_area = st.radio("Select a price area:", price_areas, key="price_area")
    filtered_area = df[df['price_area'] == selected_area]

    if filtered_area.empty:
        st.warning("No data for the selected price area.")
    else:
        pie_data = filtered_area.groupby('production_group')['production_mwh'].sum().reset_index()
        fig1 = px.pie(pie_data, names='production_group', values='production_mwh', title=f"Production share in {selected_area}")
        st.plotly_chart(fig1, use_container_width=True)

# Production group + Month + Line chart
with col2:
    st.subheader("Monthly Production Trend")

    production_groups = sorted(list({x.strip() for x in df['production_group']}))

    if production_groups:
        selected_groups = st.pills("Select production groups:", options=production_groups, selection_mode="multi", default=production_groups)
    else:
        st.warning("No production groups found.")
        selected_groups = []

    if not selected_groups:
        st.warning("Please select at least one production group to display the line chart.")
    else:
        # Month selector
        months = sorted(df['date'].dt.strftime('%B').unique())
        selected_month = st.selectbox("Select a month:", months)
        month_num = datetime.strptime(selected_month, '%B').month

        # Filter data for line chart
        filtered_line = df[
            (df['price_area'] == selected_area) &
            (df['production_group'].isin(selected_groups)) &
            (df['date'].dt.month == month_num)
        ]

        if filtered_line.empty:
            st.warning("No data available for the selected combination.")
        else:
            line_data = filtered_line.groupby(['date', 'production_group'])['production_mwh'].sum().reset_index()
            fig2 = px.line(line_data, x='date',y='production_mwh', color='production_group', title=f"Production trend in {selected_area} ({selected_month})", markers=True)
            fig2.update_layout(xaxis_title="Date", yaxis_title="Production (MWh)")
            st.plotly_chart(fig2, use_container_width=True)

# -------------------------------
# Expander for data source
# -------------------------------
with st.expander("Data Source"):
    st.markdown("""
    **Source:** Data retrieved from the Elhub API and stored in MongoDB.  
    The charts above show electricity production by price area and production group, aggregated by date.
    """)
