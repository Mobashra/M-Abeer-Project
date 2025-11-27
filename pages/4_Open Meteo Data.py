import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import utils 

st.set_page_config(page_title="Weather Statistics", layout="wide")
st.title("🌤️ Weather Data Analysis")

# --- 1. GLOBAL SETTINGS ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

current_area = st.session_state["selected_price_area"]
coords = st.session_state["selected_coords"]

st.info(f"**Analysis Scope:** {current_area} ({coords['lat']:.2f}, {coords['lon']:.2f})")

# --- 2. FETCH DATA ---
with st.spinner("Fetching weather history (2021-2024)..."):
    df_full = utils.fetch_weather_api(coords['lat'], coords['lon'], "2021-01-01", "2024-12-31")

if df_full.empty:
    st.error("No weather data available.")
    st.stop()

df_full['Year'] = df_full['time'].dt.year
df_full['Month'] = df_full['time'].dt.month

# --- 3. TABS ---
tab1, tab2 = st.tabs(["📊 Dataset Overview (First Month)", "📈 Yearly Trend Visualization"])

# ==================================================
# TAB 1: DATASET OVERVIEW (JANUARY TREND)
# ==================================================
with tab1:
    st.subheader("Dataset Overview with First Month Trends")
    st.caption("Each row represents a variable from the dataset, with a line chart showing the **January** trend.")
    
    stat_year = st.selectbox("Select Year:", [2021, 2022, 2023, 2024], index=0)
    
    # Filter for the selected Year
    df_year = df_full[df_full['Year'] == stat_year].copy()
    
    # Filter for January (First Month) for the sparkline
    df_jan = df_year[df_year['Month'] == 1].copy()
    
    if not df_year.empty:
        summary_data = []
        for var in utils.WEATHER_VARS:
            # Stats based on the FULL YEAR
            mean_val = df_year[var].mean()
            std_val = df_year[var].std()
            min_val = df_year[var].min()
            max_val = df_year[var].max()
            
            # Sparkline based on JANUARY ONLY
            jan_trend = df_jan[var].tolist()
            
            summary_data.append({
                "Variable Name": var,
                "Mean": round(mean_val, 2),
                "Std Dev": round(std_val, 2),
                "Min": round(min_val, 2),
                "Max": round(max_val, 2),
                "First Month Trend": jan_trend # Data for the graph
            })
        
        # Create DataFrame
        stats_df = pd.DataFrame(summary_data)
        
        # Display with LineChartColumn
        st.dataframe(
            stats_df,
            column_config={
                "First Month Trend": st.column_config.LineChartColumn(
                    f"Trend (Jan {stat_year})",
                    y_min=0, 
                    y_max=None # Auto-scale
                ),
                "Variable Name": st.column_config.TextColumn("Variable Name", width="medium"),
            },
            hide_index=True, 
            use_container_width=True,
            height=400 # Give it some height to look like the image
        )
    else:
        st.warning("No data.")

# ==================================================
# TAB 2: YEARLY TREND (FULL VISUALIZATION)
# ==================================================
with tab2:
    st.subheader("Yearly Trend Visualization")
    
    # --- CONTROLS ---
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        df_full['YYYY-MM'] = df_full['time'].dt.to_period('M').astype(str)
        unique_months = sorted(df_full['YYYY-MM'].unique())
        
        # Default: Full Year (First Month to Last Month of Data) to show "Yearly Trend"
        start_month, end_month = st.select_slider(
            "Select Time Range",
            options=unique_months,
            value=(unique_months[0], unique_months[-1]) 
        )
        
    with c2:
        st.write("") 
        normalize = st.checkbox("Normalize (0-1)", value=False)
        select_all = st.checkbox("Select All Variables", value=False)

    # Variable Selection
    if select_all:
        default_selection = utils.WEATHER_VARS
    else:
        default_selection = ["temperature_2m", "precipitation"]
            
    with c3:
        # Place selector in the 3rd column or below? 
        # Keeping it in a column makes it compact, but let's move it to a full row if needed.
        # For now, c3 is fine.
        pass

    # Full Width Selector
    selected_cols = st.multiselect("Variables:", utils.WEATHER_VARS, default=default_selection, key=f"vars_{select_all}")

    # --- FILTER DATA ---
    start_date = pd.to_datetime(start_month)
    end_date = (pd.to_datetime(end_month) + pd.offsets.MonthEnd(0)) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    
    mask = (df_full['time'] >= start_date) & (df_full['time'] <= end_date)
    df_plot = df_full.loc[mask].copy()

    # --- NORMALIZE ---
    if normalize:
        for col in selected_cols:
            min_v, max_v = df_plot[col].min(), df_plot[col].max()
            if max_v != min_v:
                df_plot[col] = (df_plot[col] - min_v) / (max_v - min_v)

    # --- PLOTTING ---
    fig = go.Figure()
    
    colors = {
        "temperature_2m": "#1f77b4", 
        "precipitation": "#2ca02c", 
        "wind_speed_10m": "#ff7f0e", 
        "wind_gusts_10m": "#7f7f7f", 
        "wind_direction_10m": "purple"
    }

    for col in selected_cols:
        fig.add_trace(go.Scatter(
            x=df_plot['time'], 
            y=df_plot[col], 
            mode='lines', 
            name=col,
            line=dict(width=1.5, color=colors.get(col, "black"))
        ))

    fig.update_layout(
        height=500,
        template="plotly_white",
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        margin=dict(l=40, r=40, t=80, b=40),
        xaxis=dict(title="Time", showgrid=False),
        yaxis=dict(title="Normalized Value (0-1)" if normalize else "Value", showgrid=True),
        title=f"Weather Trends ({start_month} to {end_month})"
    )

    st.plotly_chart(fig, use_container_width=True)