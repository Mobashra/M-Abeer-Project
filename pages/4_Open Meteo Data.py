import streamlit as st
import plotly.graph_objects as go
import pandas as pd
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

# --- 3. TABS ---
tab1, tab2 = st.tabs(["📊 Statistics Table", "📈 Interactive Plot"])

# ==================================================
# TAB 1: STATISTICS
# ==================================================
with tab1:
    st.subheader("Yearly Statistics")
    stat_year = st.selectbox("Select Year for Statistics:", [2021, 2022, 2023, 2024], index=0)
    
    df_stats = df_full[df_full['Year'] == stat_year].copy()
    
    if not df_stats.empty:
        summary_data = []
        for var in utils.WEATHER_VARS:
            summary_data.append({
                "Variable": var,
                "Average": round(df_stats[var].mean(), 2),
                "Std Dev": round(df_stats[var].std(), 2),
                "Min": round(df_stats[var].min(), 2),
                "Max": round(df_stats[var].max(), 2),
                "Trend": df_stats[var].tolist()
            })
        
        st.dataframe(
            pd.DataFrame(summary_data),
            column_config={"Trend": st.column_config.LineChartColumn(f"Trend ({stat_year})")},
            hide_index=True, use_container_width=True
        )
    else:
        st.warning("No data.")

# ==================================================
# TAB 2: PLOT (NEW LAYOUT)
# ==================================================
with tab2:
    st.subheader("Interactive Weather Plot")
    
    # --- ROW 1: TIME SLIDER & CHECKBOXES ---
    c1, c2 = st.columns([3, 1])
    
    with c1:
        df_full['YYYY-MM'] = df_full['time'].dt.to_period('M').astype(str)
        unique_months = sorted(df_full['YYYY-MM'].unique())
        
        # Default: Jan 2021 to Feb 2021
        start_month, end_month = st.select_slider(
            "Select Time Range",
            options=unique_months,
            value=(unique_months[0], unique_months[1]) 
        )
        
    with c2:
        st.write("") # Spacer to align with slider
        normalize = st.checkbox("Normalize (0-1)", value=False)
        select_all = st.checkbox("Select All Variables", value=False)

    # --- ROW 2: VARIABLES (FULL WIDTH) ---
    # Logic: Default to everything if checked, else just temp/precip
    if select_all:
        default_selection = utils.WEATHER_VARS
    else:
        default_selection = ["temperature_2m", "precipitation"]
        
    # Using a dynamic key ensures it resets when you click "Select All"
    selected_cols = st.multiselect(
        "Select Variables to Plot:", 
        utils.WEATHER_VARS, 
        default=default_selection,
        key=f"multiselect_{select_all}"
    )

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
        title=f"Weather Trends ({start_month} to {end_month})",
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        margin=dict(l=40, r=40, t=80, b=40),
        # AXIS LABELS (Added as requested)
        xaxis=dict(title="Time", showgrid=False),
        yaxis=dict(title="Normalized Value (0-1)" if normalize else "Value", showgrid=True)
    )

    st.plotly_chart(fig, use_container_width=True)