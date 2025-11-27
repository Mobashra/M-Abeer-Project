import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import utils 

st.set_page_config(page_title="Elhub Data Explorer", layout="wide")
st.title("📊 Elhub Data Explorer")

if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

# --- CONTROLS ---
col1, col2 = st.columns(2)
with col1:
    data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
with col2:
    selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)

# --- LOAD DATA ---
with st.spinner(f"Fetching data for {selected_year}..."):
    df = utils.get_year_data(data_type, selected_year)

if df.empty:
    st.warning(f"No data found for **{data_type}** in **{selected_year}**.")
    st.stop()

# Ensure 'price_area' column exists
if 'price_area' not in df.columns:
    st.error("Data missing 'price_area' column. Cannot continue.")
    st.stop()

val_col = 'mwh'  # Use 'mwh' consistently

# --- VISUALIZATION ---
col_left, col_right = st.columns(2)

# --- LEFT: PIE CHART ---
with col_left:
    st.subheader(f"{data_type} Share")
    
    price_areas = sorted(df['price_area'].unique())
    curr = st.session_state["selected_price_area"]
    idx = price_areas.index(curr) if curr in price_areas else 0
    selected_area = st.selectbox("Price Area:", price_areas, index=idx)
    
    if selected_area != st.session_state["selected_price_area"]:
        st.session_state["selected_price_area"] = selected_area
        st.rerun()

    df_area = df[df['price_area'] == selected_area]
    pie_data = df_area.groupby('group')[val_col].sum().reset_index().sort_values(val_col, ascending=False)

    fig1 = go.Figure(data=[go.Pie(
        labels=pie_data['group'],
        values=pie_data[val_col],
        hole=0.0,
        rotation=45,
        pull=[0]*len(pie_data),  # no explode
        marker=dict(colors=px.colors.qualitative.Pastel, line=dict(width=0)),
        textinfo='label+percent',
        textposition='auto',
        insidetextorientation='horizontal'
    )])

    fig1.update_layout(
        title=dict(
            text=f"Total {data_type} in {selected_area}",
            x=0.0,
            y=0.95,
            xanchor='left',
            yanchor='top'
        ),
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
        margin=dict(t=100, b=80, l=80, r=80)
    )

    st.plotly_chart(fig1, use_container_width=True)

# --- RIGHT: DAILY LINE CHART ---
with col_right:
    st.subheader("Daily Trend")
    if not df_area.empty:
        all_groups = sorted(df_area['group'].unique())
        sel_groups = st.multiselect("Filter Groups:", all_groups, default=all_groups)
        
        if sel_groups:
            df_line = df_area[df_area['group'].isin(sel_groups)].copy()
            df_line.set_index('date', inplace=True)
            df_line.sort_index(inplace=True)

            # Ensure continuous dates to prevent horizontal lines in SPC/LOF
            full_idx = pd.date_range(df_line.index.min().normalize(), df_line.index.max().normalize(), freq='D')
            df_line = df_line.groupby('group')[val_col].resample('D').sum().reindex(full_idx, fill_value=0).reset_index()
            df_line.rename(columns={'index': 'date'}, inplace=True)

            fig2 = px.line(
                df_line,
                x='date',
                y=val_col,
                color='group',
                title=f"Daily {data_type} over Time",
                labels={val_col: 'MWh', 'date': 'Date'}
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No data for this area.")

# --- RAW DATA ---
with st.expander("🔎 View Data"):
    st.dataframe(df.head(200), use_container_width=True)
