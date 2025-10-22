import streamlit as st
import pymongo
import pandas as pd

# Load MongoDB secrets
mongo_uri = st.secrets["mongo"]["uri"]
mongo_db = st.secrets["mongo"]["database"]
mongo_collection = st.secrets["mongo"]["collection"]

# Connect to MongoDB
client = pymongo.MongoClient(mongo_uri)
db = client[mongo_db]
collection = db[mongo_collection]

# Load data into a DataFrame
data = pd.DataFrame(list(collection.find()))

# Optional: Drop the MongoDB default `_id` column if not needed
if "_id" in data.columns:
    data = data.drop(columns=["_id"])

# Preview
st.write("Sample data from MongoDB:")
st.dataframe(data.head())
