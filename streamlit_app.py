import streamlit as st
import plotly.express as px
import plotly.graph_objects as go # Need this for the highlight trace
import pandas as pd
import utils

st.set_page_config(page_title="Norwegian Energy Atlas", layout="wide")

st.title("🇳🇴 Regional Energy Overview")
st.info("Select Data Type, Year, and Region to set the context for analysis.")

# --- 1. INITIALIZE STATE ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
if "selected_coords" not in st.session_state:
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

# --- 2. CONTROLS ---
c1, c2, c3 = st.columns(3)
with c1:
    data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
with c2:
    year = st.selectbox("Year", [2021, 2022, 2023, 2024], index=3)
with c3:
    days = st.slider(f"Days to Aggregate (Ending Dec 31, {year})", 7, 365, 30)

c4, c5 = st.columns(2)
with c4:
    if data_type == "Production":
        groups = ["hydro", "wind", "thermal", "solar", "other"]
    else:
        groups = ["cabin", "household", "primary", "secondary", "tertiary"]
    selected_group = st.selectbox(f"{data_type} Group:", groups, index=0)

with c5:
    all_areas = sorted(list(utils.CITIES.keys()))
    curr = st.session_state["selected_price_area"]
    idx = all_areas.index(curr) if curr in all_areas else 0
    
    # If user changes this dropdown, the map will reload with the highlight!
    selected_area = st.selectbox("Select Region (Highlights Map):", all_areas, index=idx)
    
    if selected_area != st.session_state["selected_price_area"]:
        st.session_state["selected_price_area"] = selected_area
        city = utils.CITIES[selected_area]
        st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
        st.rerun()

# --- 3. LOAD DATA ---
with st.spinner(f"Loading {selected_group} data for {year}..."):
    df = utils.load_map_data(target_year=year, days_to_agg=days, data_type=data_type, selected_group=selected_group)
    geojson = utils.load_geojson()

if df.empty:
    st.warning(f"No data found for **{selected_group}** in **{year}**. Try selecting a different group.")
    st.stop()

if not geojson:
    st.error("GeoJSON file not found.")
    st.stop()

# --- 4. MAP PREPARATION ---
df_map = df.groupby('price_area')['val'].mean().reset_index()
df_map['price_area_map'] = df_map['price_area'].str.replace("NO", "NO ")

st.subheader(f"Mean {selected_group.capitalize()} {data_type} ({year})")

# Base Choropleth
fig = px.choropleth_mapbox(
    df_map, 
    geojson=geojson, 
    locations='price_area_map', 
    featureidkey="properties.ElSpotOmr",
    color='val', 
    color_continuous_scale="Viridis", 
    mapbox_style="carto-positron",
    zoom=4.5, 
    center={"lat": 64, "lon": 12}, 
    opacity=0.5,
    labels={'val': 'MWh'}
)

# --- HIGHLIGHT SELECTED AREA (NEW FEATURE) ---
# We filter the GeoJSON to find ONLY the selected area polygon
selected_area_map_name = st.session_state["selected_price_area"].replace("NO", "NO ") # "NO1" -> "NO 1"

highlight_feature = None
for feature in geojson["features"]:
    if feature["properties"]["ElSpotOmr"] == selected_area_map_name:
        highlight_feature = feature
        break

if highlight_feature:
    # Add a second trace that draws JUST the border of the selected area
    # We use a transparent fill but a thick Red Line
    fig.add_trace(go.Choroplethmapbox(
        geojson=geojson,
        locations=[selected_area_map_name],
        featureidkey="properties.ElSpotOmr",
        z=[1], # Dummy value
        colorscale=[[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']], # Transparent fill
        marker_line_color='red', # THE HIGHLIGHT COLOR
        marker_line_width=4,     # THICKNESS
        showscale=False,
        hoverinfo='skip'
    ))
# --------------------------------------------

fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

# --- 5. CLICK INTERACTION ---
event = st.plotly_chart(fig, on_select="rerun", selection_mode="points", use_container_width=True)

if event and event["selection"]["points"]:
    point = event["selection"]["points"][0]
    
    if "lat" in point:
        st.session_state["selected_coords"] = {"lat": point["lat"], "lon": point["lon"]}
    
    if "location" in point:
        area_clicked = point["location"].replace(" ", "")
        if area_clicked in utils.CITIES and area_clicked != st.session_state["selected_price_area"]:
            st.session_state["selected_price_area"] = area_clicked
            city = utils.CITIES[area_clicked]
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

curr_area = st.session_state["selected_price_area"]
st.success(f"✅ **Active Region:** {curr_area} (Highlighted in Red)")