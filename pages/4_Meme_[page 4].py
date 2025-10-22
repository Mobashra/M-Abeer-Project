import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pymongo import MongoClient
from datetime import datetime

# -------------------------------
# Page setup
# -------------------------------
st.set_page_config(page_title="Page 4 - Electricity Data", layout="wide")
st.title("Electricity Production Overview")

# -------------------------------
# MongoDB connection
# -------------------------------
@st.cache_resource
def get_mongo_collection():
    client = MongoClient(st.secrets["mongo"]["uri"])
    db = client[st.secrets["mongo"]["database"]]
    collection = db[st.secrets["mongo"]["collection"]]
    return collection

collection = get_mongo_collection()

# -------------------------------
# Load and preprocess data
# -------------------------------
data = list(collection.find())
df = pd.DataFrame(data)

# Ensure production_group and price_area are clean
df['production_group'] = df['production_group'].fillna("Unknown").astype(str)
df['price_area'] = df['price_area'].fillna("Unknown").astype(str)

# Convert timestamps to datetime
df['date'] = pd.to_datetime(df['start_time'], unit='ms')

# Rename for clarity
df.rename(columns={'value': 'production_mwh'}, inplace=True)

# -------------------------------
# Layout with two columns
# -------------------------------
col1, col2 = st.columns(2)

# ----- LEFT: Price area + Pie chart -----
with col1:
    st.subheader("Production Share by Price Area")

    price_areas = sorted(df['price_area'].unique())
    selected_area = st.radio("Select a price area:", price_areas)

    filtered_area = df[df['price_area'] == selected_area]
    pie_data = filtered_area.groupby('production_group')['production_mwh'].sum()

    fig1, ax1 = plt.subplots()
    ax1.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
    ax1.set_title(f"Production share in {selected_area}")
    st.pyplot(fig1)

# ----- RIGHT: Production group + Month + Line chart -----
with col2:
    st.subheader("Monthly Production Trend")

    # Unique production groups
    production_groups = sorted(df['production_group'].unique().tolist())

    if production_groups:
        selected_groups = st.pills(
            "Select production groups:",
            options=production_groups,
            selection_mode="multi",
            default=production_groups  # all selected by default
        )
    else:
        st.warning("No production groups found in the data.")
        selected_groups = []

    # Month selector
    months = sorted(df['date'].dt.strftime('%B').unique())
    selected_month = st.selectbox("Select a month:", months)
    month_num = datetime.strptime(selected_month, '%B').month

    # Filter data for line plot
    filtered = df[
        (df['price_area'] == selected_area) &
        (df['production_group'].isin(selected_groups)) &
        (df['date'].dt.month == month_num)
    ]

    # Group by date and production_group
    line_data = filtered.groupby(['date', 'production_group'])['production_mwh'].sum().reset_index()

    # Plot line chart
    fig2, ax2 = plt.subplots()
    for group in selected_groups:
        grp_data = line_data[line_data['production_group'] == group]
        ax2.plot(grp_data['date'], grp_data['production_mwh'], label=group)

    ax2.set_title(f"Production trend in {selected_area} ({selected_month})")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Production (MWh)")
    ax2.legend()
    st.pyplot(fig2)

# -------------------------------
# Expander for data source
# -------------------------------
with st.expander("Data Source"):
    st.markdown("""
    **Source:** Data retrieved from the Elhub API and stored in MongoDB.  
    The charts above show electricity production by price area and production group, aggregated by date.
    """)
