import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import utils


# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Norwegian Energy Atlas", layout="wide")
st.title("🇳🇴 Regional Energy Overview")


st.info("This page defines the **global context** used across the entire Energy Atlas. "
       "Select the data source, year, aggregation window, and region.")


# ======================================================
# 1. INIT SESSION STATE
# ======================================================
if "selected_price_area" not in st.session_state:
   st.session_state["selected_price_area"] = "NO1"


if "selected_coords" not in st.session_state:
   default = utils.CITIES["NO1"]
   st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}


current_area = st.session_state["selected_price_area"]


# ======================================================
# 2. CONTROLS
# ======================================================
c1, c2, c3 = st.columns(3)


with c1:
   data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)


with c2:
   year = st.selectbox("Year", [2021, 2022, 2023, 2024], index=3)


with c3:
   days = st.slider(f"Days to Aggregate (ending Dec 31, {year})", min_value=7, max_value=365, value=30)


c4, c5 = st.columns(2)


# --- GROUP SELECTOR ---
with c4:
   groups = (
       ["hydro", "wind", "thermal", "solar", "other"]
       if data_type == "Production"
       else ["cabin", "household", "primary", "secondary", "tertiary"]
   )
   selected_group = st.selectbox(f"{data_type} Group", groups)


# --- REGION SELECTOR ---
with c5:
   area_list = sorted(utils.CITIES.keys())
   selected_area = st.selectbox("Region (Map Highlight)", area_list, index=area_list.index(current_area))


   if selected_area != current_area:
       st.session_state["selected_price_area"] = selected_area
       city = utils.CITIES[selected_area]
       st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
       st.rerun()


# ======================================================
# 3. LOAD MAP DATA
# ======================================================
with st.spinner(f"Loading {selected_group} data for {year}..."):
   df = utils.load_map_data(
       target_year=year,
       days_to_agg=days,
       data_type=data_type,
       selected_group=selected_group
   )
   geojson = utils.load_geojson()


if df.empty:
   st.warning(f"No data found for **{selected_group}** in {year}.")
   st.stop()


if not geojson:
   st.error("Failed to load GeoJSON. Map cannot be displayed.")
   st.stop()


# Ensure map label column exists
df["price_area_map"] = df["price_area"].astype(str).str.replace("NO", "NO ")


# ======================================================
# 4. CHOROPLETH MAP
# ======================================================
st.subheader(f"Mean {selected_group.capitalize()} {data_type} ({year})")


fig = px.choropleth_mapbox(
   df,
   geojson=geojson,
   locations="price_area_map",
   featureidkey="properties.ElSpotOmr",
   color="val",
   color_continuous_scale="Viridis",
   mapbox_style="carto-positron",
   zoom=4.5,
   center={"lat": 64, "lon": 12},
   opacity=0.55,
   labels={"val": "MWh"},
)


# --- Highlight selected region ---
highlight_name = current_area.replace("NO", "NO ")


fig.add_trace(
   go.Choroplethmapbox(
       geojson=geojson,
       locations=[highlight_name],
       featureidkey="properties.ElSpotOmr",
       z=[1],
       colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
       marker_line_color="red",
       marker_line_width=4,
       showscale=False,
       hoverinfo="skip",
   )
)


fig.update_layout(margin=dict(r=0, t=0, l=0, b=0))


# ======================================================
# 5. INTERACTION HANDLER
# ======================================================
event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")


if event and "selection" in event and event["selection"]["points"]:
   point = event["selection"]["points"][0]


   # Update coordinates if available
   if "lat" in point:
       st.session_state["selected_coords"] = {"lat": point["lat"], "lon": point["lon"]}


   if "location" in point:
       clicked = point["location"].replace(" ", "")
       if clicked in utils.CITIES and clicked != current_area:
           st.session_state["selected_price_area"] = clicked
           city = utils.CITIES[clicked]
           st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
           st.rerun()


# ======================================================
# 6. FOOTER STATUS
# ======================================================
st.success(f"✅ Active Region: {st.session_state['selected_price_area']} "
          f"({st.session_state['selected_coords']['lat']:.2f}, {st.session_state['selected_coords']['lon']:.2f})")


