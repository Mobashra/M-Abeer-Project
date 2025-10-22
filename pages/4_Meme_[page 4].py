



import streamlit as st
import pymongo
import pandas as pd




from pymongo import MongoClient

client = MongoClient(st.secrets["mongo"]["uri"])
db = client[st.secrets["mongo"]["database"]]
collection = db[st.secrets["mongo"]["collection"]]


# Connect to MongoDB


# Load data into a DataFrame
data = pd.DataFrame(list(collection.find()))

# Optional: Drop the MongoDB default `_id` column if not needed
if "_id" in data.columns:
    data = data.drop(columns=["_id"])

# Preview
st.write("Sample data from MongoDB:")
st.dataframe(data.head())
