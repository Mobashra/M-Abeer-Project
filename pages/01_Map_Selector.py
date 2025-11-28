import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import utils
from datetime import date
from shapely.geometry import shape, Point

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Map Selector", layout="wide")

# Sidebar
utils.render_sidebar()

st.title("🇳🇴 Regional Energy Overview")

# ======================================================
# 1. INIT STATE
# ======================================================
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

current_area = st.session_state["selected_price_area"]

# ======================================================
# 2. CONTROLS
# ======================================================
with st.container():
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown("###### Source")
        data_type = st.radio(
            "Source", ["Production", "Consumption"],
            horizontal=True, label_visibility="collapsed"
        )

    with c2:
        st.markdown("###### Start Date")
        start_d = st.date_input(
            "Start", date(2021, 1, 1),
            min_value=date(2021, 1, 1),
            max_value=date(2024, 12, 31),
            label_visibility="collapsed"
        )

    with c3:
        st.markdown("###### End Date")
        end_d = st.date_input(
            "End", date(2021, 12, 31),
            min_value=date(2021, 1, 1),
            max_value=date(2024, 12, 31),
            label_visibility="collapsed"
        )

    with c4:
        st.markdown("###### Group")
        groups = (
            ["hydro", "wind", "thermal", "solar", "other"]
            if data_type == "Production"
            else ["cabin", "household", "primary", "secondary", "tertiary"]
        )
        selected_group = st.selectbox("Group", groups, label_visibility="collapsed")

    with c5:
        st.markdown("###### Region")
        area_list = sorted(utils.CITIES.keys())
        manual_area = st.selectbox(
            "Region", area_list,
            index=area_list.index(st.session_state["selected_price_area"]),
            label_visibility="collapsed"
        )
        if manual_area != st.session_state["selected_price_area"]:
            st.session_state["selected_price_area"] = manual_area
            city = utils.CITIES[manual_area]
            st.session_state["selected_coords"] = {
                "lat": city["lat"], "lon": city["lon"]
            }
            st.rerun()

# Validate date range
if start_d > end_d:
    st.error("Start Date must be before End Date.")
    st.stop()

st.divider()

# ======================================================
# 3. LOAD MAP DATA
# ======================================================
with st.spinner("Loading Map Data..."):
    df = utils.load_map_stats(start_d, end_d, data_type, selected_group)
    geojson_areas = utils.load_geojson()
    geojson_munis = utils.load_municipality_geojson()

if not geojson_areas:
    st.error("❌ Missing required file: elspot_areas.geojson")
    st.stop()

if not df.empty:
    df["price_area_map"] = df["price_area"].astype(str).replace("NO", "NO ", regex=False)

# ------------------------------------------------------
# Hit-test price area from coordinates
# ------------------------------------------------------
def get_clicked_area_id(lat, lon, gj):
    point = Point(lon, lat)
    for f in gj["features"]:
        try:
            geom = shape(f["geometry"])
            if geom.contains(point):
                return (
                    f["properties"].get("ElSpotOmr")
                    or f["properties"].get("ElSpot_omr")
                )
        except:
            continue
    return None

# ------------------------------------------------------
# Build centroid click points (municipalities)
# ------------------------------------------------------
click_points = []
if geojson_munis:
    for f in geojson_munis["features"]:
        try:
            geom = shape(f["geometry"])
            c = geom.centroid
            name = (
                f["properties"]["navn"][0]["navn"]
                if isinstance(f["properties"].get("navn"), list)
                else f["properties"].get("navn", "Unknown")
            )
            click_points.append({"lat": c.y, "lon": c.x, "name": name})
        except:
            pass

df_clicks = pd.DataFrame(click_points)

# ======================================================
# 4. MAP VISUALIZATION
# ======================================================
c_map, c_info = st.columns([3, 1])

with c_map:
    show_munis = st.toggle("🔍 Show Municipalities", value=False)
    feature_key = "properties.ElSpotOmr"

    # ------------------------------
    # LAYER 1 — Price Area Map (colored)
    # ------------------------------
    if not df.empty:
        fig = px.choropleth_mapbox(
            df,
            geojson=geojson_areas,
            locations="price_area_map",
            featureidkey=feature_key,
            color="avg_value",
            color_continuous_scale="Viridis",
            mapbox_style="carto-positron",
            zoom=4.5,
            center={"lat": 65, "lon": 16},
            opacity=0.6,
        )
    else:
        fig = px.choropleth_mapbox(
            geojson=geojson_areas,
            locations=["NO 1"],
            featureidkey=feature_key,
            mapbox_style="carto-positron",
            zoom=4.5,
            center={"lat": 65, "lon": 16},
        )

    # Hover shows region name + value
    fig.update_traces(
        hovertemplate="<b>%{location}</b><br>MWh: %{z:.2f}<extra></extra>"
    )

    # ------------------------------
    # LAYER 2 — Municipal Borders
    # ------------------------------
    if show_munis and geojson_munis:
        first = geojson_munis["features"][0]["properties"]
        muni_key = (
            "properties.nummer"
            if "nummer" in first
            else (
                "properties.kommunenummer"
                if "kommunenummer" in first
                else "properties.id"
            )
        )

        locs = [f["properties"].get(muni_key.split(".")[1]) for f in geojson_munis["features"]]

        fig.add_trace(go.Choroplethmapbox(
            geojson=geojson_munis,
            locations=locs,
            featureidkey=muni_key,
            z=[1] * len(locs),
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            marker_line_color="gray",
            marker_line_width=0.8,
            showscale=False,
            hoverinfo="skip",
        ))

    # ------------------------------
    # LAYER 3 — Clickable Centroids (transparent)
    # ------------------------------
    if not df_clicks.empty:
        fig.add_trace(go.Scattermapbox(
            lat=df_clicks["lat"],
            lon=df_clicks["lon"],
            mode="markers",
            marker={"size": 12, "opacity": 0.01},
            text=df_clicks["name"],
            hoverinfo="text",
        ))

    # ------------------------------
    # LAYER 4 — Highlight Selected Price Area
    # ------------------------------
    highlight = st.session_state["selected_price_area"].replace("NO", "NO ")
    fig.add_trace(go.Choroplethmapbox(
        geojson=geojson_areas,
        locations=[highlight],
        featureidkey=feature_key,
        z=[1],
        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
        marker_line_color="red",
        marker_line_width=4,
        showscale=False,
        hoverinfo="skip",
    ))

    # ------------------------------
    # LAYER 5 — Red Pin
    # ------------------------------
    coords = st.session_state["selected_coords"]
    fig.add_trace(go.Scattermapbox(
        lat=[coords["lat"]],
        lon=[coords["lon"]],
        mode="markers",
        marker={"size": 14, "color": "red"},
        text=["📍 Pin"],
        hoverinfo="text",
    ))

    fig.update_layout(
        margin=dict(r=0, l=0, t=0, b=0),
        clickmode="event+select",
        height=820,
    )

    # ------------------------------
    # EVENT HANDLER
    # ------------------------------
    event = st.plotly_chart(
        fig, use_container_width=True,
        on_select="rerun", selection_mode="points"
    )

    if event and "selection" in event and event["selection"]["points"]:
        p = event["selection"]["points"][0]

        # Update pin coordinates
        if "lat" in p:
            st.session_state["selected_coords"] = {"lat": p["lat"], "lon": p["lon"]}

            # Fetch elevation robustly
            elev = utils.fetch_elevation(p["lat"], p["lon"])
            if elev is not None:
                st.session_state["elevation"] = elev
            else:
                st.session_state["elevation"] = "N/A"

            # Update selected price area
            hit = get_clicked_area_id(p["lat"], p["lon"], geojson_areas)
            if hit:
                clean = hit.replace(" ", "")
                if clean in utils.CITIES:
                    st.session_state["selected_price_area"] = clean

            st.rerun()

        # Polygon click fallback
        elif "location" in p:
            clicked = p["location"].replace(" ", "")
            if clicked in utils.CITIES:
                st.session_state["selected_price_area"] = clicked
                st.rerun()

# ======================================================
# 5. RIGHT PANEL — SELECTION INFO
# ======================================================
with c_info:
    st.markdown("## 📍 Selection Details")

    # ACTIVE REGION
    region = st.session_state["selected_price_area"]
    center = utils.CITIES[region]
    st.info(f"### {region}")
    st.caption(f"Center: {center['lat']:.2f}, {center['lon']:.2f}")

    st.divider()

    # PIN LOCATION
    st.markdown("### 📌 Pin Location")
    pin = st.session_state["selected_coords"]
    st.write(f"**Lat:** {pin['lat']:.4f}")
    st.write(f"**Lon:** {pin['lon']:.4f}")

    st.divider()

    # ELEVATION
    st.markdown("### ⛰️ Elevation")
    elev = st.session_state.get("elevation", "Click map")
    st.metric("", f"{elev if elev != 'N/A' else 'Not Available'}")
