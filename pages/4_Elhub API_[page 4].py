import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import plotly.express as px


# Page setup
st.set_page_config(page_title="New Data", layout="wide")  # Setting page title and wide layout
st.title("Elhub API Data")  # Displaying the page header


# MongoDB connection with caching
@st.cache_resource  # Caching the MongoDB connection to avoid repeated reconnects
def get_mongo_collection():
    client = MongoClient(st.secrets["mongo"]["uri"])  # Connecting to MongoDB using secrets
    db = client[st.secrets["mongo"]["database"]]  # Selecting the database
    collection = db[st.secrets["mongo"]["collection"]]  # Selecting the collection
    return collection

collection = get_mongo_collection()  # Getting the collection

# Load and preprocess data with caching
@st.cache_data(ttl=600)  # Caching the data for 10 minutes,idea from IND320 notebook
def load_data():
    data = list(collection.find())  # Retrieving all documents from MongoDB
    df = pd.DataFrame(data)  # Converting to pandas DataFrame

    if df.empty:  # Returning immediately if collection is empty
        return df

    # Cleaning missing values and converting types
    df['production_group'] = df['production_group'].fillna("Unknown").astype(str)
    df['price_area'] = df['price_area'].fillna("Unknown").astype(str)

    # Converting timestamp to datetime
    df['date'] = pd.to_datetime(df['start_time'], unit='ms')

    # Renaming value column for clarity
    df.rename(columns={'value': 'production_mwh'}, inplace=True)
    return df

df = load_data()  # Loading and preprocessing the data

if df.empty:  # Stopping the app if no data is found
    st.warning("No data found in the MongoDB collection.")
    st.stop()


# Layout with two columns (Task requirement)
col1, col2 = st.columns(2)  # Splitting page into two columns


# Left column: Pie chart for production share by price area
with col1:
    st.subheader("Production Share by Price Area")

    # Selecting a price area using radio buttons (interactive selection)
    price_areas = sorted(df['price_area'].unique())
    selected_area = st.radio("Select a price area:", price_areas, key="price_area")

    # Filtering data for the selected price area
    filtered_area = df[df['price_area'] == selected_area]

    if filtered_area.empty:
        st.warning("No data for the selected price area.")
    else:
        # Aggregating total production per production group for pie chart
        pie_data = filtered_area.groupby('production_group')['production_mwh'].sum().reset_index()

        # Creating interactive pie chart with Plotly
        fig1 = px.pie(pie_data, names='production_group', values='production_mwh', title=f"Production share in {selected_area}")
        st.plotly_chart(fig1, use_container_width=True)  # Displaying the pie chart


# Right column: Line chart for monthly production trend
with col2:
    st.subheader("Monthly Production Trend")

    # Selecting production groups using pills (interactive multi-selection)
    production_groups = sorted(list({x.strip() for x in df['production_group']}))
    if production_groups:
        selected_groups = st.pills("Select production groups:", options=production_groups, selection_mode="multi", default=production_groups)
    else:
        st.warning("No production groups found.")
        selected_groups = []

    if not selected_groups:
        st.warning("Please select at least one production group to display the line chart.")
    else:
        # Selecting month for filtering data
        months = sorted(df['date'].dt.strftime('%B').unique())
        selected_month = st.selectbox("Select a month:", months)
        month_num = datetime.strptime(selected_month, '%B').month

        # Filtering data based on selected price area, production group(s), and month
        filtered_line = df[(df['price_area'] == selected_area) & (df['production_group'].isin(selected_groups)) & (df['date'].dt.month == month_num)]

        if filtered_line.empty:
            st.warning("No data available for the selected combination.")
        else:
            # Aggregating production per date and production group for line chart
            line_data = filtered_line.groupby(['date', 'production_group'])['production_mwh'].sum().reset_index()

            # Creating interactive line chart with Plotly
            fig2 = px.line(line_data, x='date', y='production_mwh',color='production_group', title=f"Production trend in {selected_area} ({selected_month})", markers=True)
            fig2.update_layout(xaxis_title="Date", yaxis_title="Production (MWh)")

            # Displaying the line chart
            st.plotly_chart(fig2, use_container_width=True)


# Expander for data source
with st.expander("Data Source"):
    # Including clickable link to Elhub API for reference
    st.markdown("""
    **Source:** Data retrieved from the [Elhub API](https://api.elhub.no) and stored in MongoDB.  
    The charts above show electricity production by price area and production group, aggregated by date.
    """)
