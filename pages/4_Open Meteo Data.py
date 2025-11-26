import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import utils
import numpy as np # Needed for variance/std calculations

st.set_page_config(page_title="Weather Statistics", layout="wide")
st.title("🌤️ Weather Data Analysis")

# --- 1. GLOBAL SETTINGS ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

current_area = st.session_state["selected_price_area"]
coords = st.session_state["selected_coords"]

# Blue Context Box
st.info(f"""
**Analysis Scope:**
* **Location:** {current_area} ({coords['lat']:.2f}, {coords['lon']:.2f})
""")

# --- 2. FETCH DATA (FULL HISTORY) ---
# We load all 4 years once so both tabs can use it instantly
with st.spinner("Fetching weather history (2021-2024)..."):
    df_full = utils.fetch_weather_api(coords['lat'], coords['lon'], "2021-01-01", "2024-12-31")

if df_full.empty:
    st.error("No weather data available.")
    st.stop()

# Create "Year" column for filtering
df_full['Year'] = df_full['time'].dt.year

# --- 3. TABS ---
tab1, tab2 = st.tabs(["📊 Statistics & Trends", "📈 Advanced Visualization"])

# ==================================================
# TAB 1: STATISTICS TABLE (Mean, Variance, Sparkline)
# ==================================================
with tab1:
    st.subheader("Yearly Statistics")
    
    # Filter by Year (Stats are usually viewed per year)
    stat_year = st.selectbox("Select Year for Statistics:", [2021, 2022, 2023, 2024], index=3)
    
    # Filter Data
    df_stats = df_full[df_full['Year'] == stat_year].copy()
    
    if not df_stats.empty:
        summary_data = []
        for var in utils.WEATHER_VARS:
            # Calculate Stats
            mean_val = df_stats[var].mean()
            std_val = df_stats[var].std() # Standard Deviation (Square root of Variance)
            min_val = df_stats[var].min()
            max_val = df_stats[var].max()
            
            summary_data.append({
                "Variable": var,
                "Average": round(mean_val, 2),
                "Std Dev (Variance)": round(std_val, 2),
                "Min": round(min_val, 2),
                "Max": round(max_val, 2),
                # Sparkline requires a list of values
                "Trend Line": df_stats[var].tolist()
            })
        
        # Display Table with Sparklines
        st.dataframe(
            pd.DataFrame(summary_data),
            column_config={
                "Trend Line": st.column_config.LineChartColumn(
                    f"Trend ({stat_year})",
                    y_min=0,
                    y_max=None  # Auto-scale
                )
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning(f"No data available for {stat_year}.")

# ==================================================
# TAB 2: ADVANCED VISUALIZATION (Normalization + Arrows)
# ==================================================
with tab2:
    st.subheader("Interactive Weather Plot")
    
    # Controls
    c1, c2 = st.columns([3, 1])
    with c1:
        # Slider for full range (2021-2024)
        df_full['YYYY-MM'] = df_full['time'].dt.to_period('M').astype(str)
        unique_months = sorted(df_full['YYYY-MM'].unique())
        
        start_month, end_month = st.select_slider(
            "Select Time Range",
            options=unique_months,
            value=(unique_months[-12], unique_months[-1]) # Default last 12 months
        )
    with c2:
        normalize = st.checkbox("Normalize (0-1 scale)", value=True, help="Scales all variables between 0 and 1 for easy comparison.")

    # Column Selection
    selected_cols = st.multiselect("Select variables:", utils.WEATHER_VARS, default=["temperature_2m", "precipitation", "wind_speed_10m"])

    # Filter Data by Date Range
    start_date = pd.to_datetime(start_month)
    end_date = (pd.to_datetime(end_month) + pd.offsets.MonthBegin(1)) + pd.offsets.MonthEnd(1)
    
    mask = (df_full['time'] >= start_date) & (df_full['time'] <= end_date)
    filtered_df = df_full.loc[mask].copy()

    # Normalization Logic
    if normalize:
        for col in selected_cols:
            min_v = filtered_df[col].min()
            max_v = filtered_df[col].max()
            if max_v != min_v:
                filtered_df[col] = (filtered_df[col] - min_v) / (max_v - min_v)

    # Plotting
    fig = go.Figure()
    
    # Defined colors for consistency
    colors = {"temperature_2m": "#1f77b4", "precipitation": "#2ca02c", "wind_speed_10m": "#ff7f0e", "wind_gusts_10m": "#7f7f7f", "wind_direction_10m": "purple"}

    for col in selected_cols:
        if col == "wind_direction_10m": continue # Don't plot direction as a line, it's messy
        
        fig.add_trace(go.Scatter(
            x=filtered_df['time'], 
            y=filtered_df[col], 
            mode='lines', 
            name=col,
            line=dict(width=1.5, color=colors.get(col, "black"))
        ))

    # Wind Arrows (if requested or if wind speed is shown)
    # We show arrows if Wind Speed is selected OR explicitly requested
    if "wind_speed_10m" in selected_cols:
        # Downsample arrows to avoid clutter (1 arrow every ~24 hours approx, or dynamic)
        step = max(1, len(filtered_df) // 40)
        arrow_data = filtered_df.iloc[::step]
        
        fig.add_trace(go.Scatter(
            x=arrow_data['time'],
            y=[-0.05] * len(arrow_data), # Put arrows at bottom
            mode='markers',
            marker=dict(
                symbol="arrow-up",
                size=10,
                angle=arrow_data['wind_direction_10m'], # Rotate arrow
                color="teal"
            ),
            name="Wind Direction (Arrow)",
            hoverinfo="skip"
        ))

    fig.update_layout(
        height=600,
        template="plotly_white",
        legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"),
        yaxis=dict(title="Normalized Value (0-1)" if normalize else "Value", showgrid=True, gridcolor='#f0f0f0'),
        margin=dict(l=40, r=40, t=40, b=80)
    )

    st.plotly_chart(fig, use_container_width=True)