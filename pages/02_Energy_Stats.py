import streamlit as st
import plotly.express as px
import plotly.graph_objects as go  # Required for your custom Pie Chart
import pandas as pd
import utils

st.set_page_config(page_title="Energy Stats", layout="wide")

# 1. SAFETY & STYLING (The New Architecture)
utils.check_session_state()
utils.render_sidebar()

# 2. HEADER
# We display the area selected from the Map Page (No local selector)
current_area = st.session_state["selected_price_area"]
st.title(f"📊 Energy Data Explorer: {current_area}")

# 3. CONTROLS (Dashboard Style)
with st.container():
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
    with c2:
        selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)
    with c3:
        st.info(f"**Context:** Showing {data_type} data for **{current_area}** in **{selected_year}**.")

st.divider()

# 4. LOAD DATA
with st.spinner(f"Fetching data for {selected_year}..."):
    df = utils.load_yearly_data(data_type, selected_year)

if df.empty:
    st.error(f"No data found for **{data_type}** in **{selected_year}**.")
    st.stop()

# Filter for the Active Region (Inherited from Home Page)
df_area = df[df['price_area'] == current_area].copy()

if df_area.empty:
    st.warning(f"No data available for **{current_area}**.")
    st.stop()

# Smart Column Detection (from your original code)
val_col = 'mwh' # utils.py normalizes this to 'mwh'

# 5. VISUALIZATION LAYOUT
col_left, col_right = st.columns(2)

# --- LEFT: THE "PRETTY" PIE CHART (Your Original Logic) ---
with col_left:
    st.subheader(f"{data_type} Share")
    
    # Aggregate
    pie_data = df_area.groupby('group')[val_col].sum().reset_index()
    pie_data = pie_data.sort_values(val_col, ascending=False)

    # Build Custom Figure
    fig1 = go.Figure(data=[go.Pie(
        labels=pie_data['group'],
        values=pie_data[val_col],
        hole=0.4,  # Donut style (0.0 was in your code, 0.4 is modern, adjust as you like)
        rotation=45,
        pull=[0.05] * len(pie_data),
        marker=dict(
            colors=px.colors.qualitative.Pastel,
            line=dict(width=0) # No border
        ),
        textinfo='label+percent',
        textposition='auto',
        insidetextorientation='horizontal'
    )])

    # Custom Layout
    fig1.update_layout(
        title=dict(text=f"Total {data_type} Mix", x=0, xanchor='left'),
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=50, b=50, l=20, r=20)
    )

    st.plotly_chart(fig1, use_container_width=True)

# --- RIGHT: LINE CHART WITH FILTER (Your Original Logic) ---
with col_right:
    st.subheader("Daily Trend")
    
    # Group Filter
    all_groups = sorted(df_area['group'].unique())
    sel_groups = st.multiselect("Filter Groups:", all_groups, default=all_groups)
    
    if sel_groups:
        # Filter Data
        df_line = df_area[df_area['group'].isin(sel_groups)].copy()
        
        # Resample to Daily (Safe Handling)
        if not pd.api.types.is_datetime64_any_dtype(df_line['date']):
            df_line['date'] = pd.to_datetime(df_line['date'])
            
        # Aggregate Daily
        line_data = df_line.set_index('date').groupby('group')[val_col].resample('D').sum().reset_index()
        
        # Plot
        fig2 = px.line(
            line_data,
            x='date',
            y=val_col,
            color='group',
            title=f"Daily {data_type} over Time",
            labels={val_col: 'MWh', 'date': 'Date'},
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig2.update_layout(hovermode="x unified", height=500, legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Select at least one group to view trends.")

# --- RAW DATA EXPANDER (Your Original Logic) ---
with st.expander("🔎 View Raw Data"):
    st.dataframe(df_area.head(200), use_container_width=True)