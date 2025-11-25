import streamlit as st
import plotly.express as px
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

# --- LOAD DATA (FAST AGGREGATION) ---
with st.spinner(f"Calculating {data_type} stats for {selected_year}..."):
    # This function returns TWO dataframes: one for Pie, one for Line
    pie_df, line_df = utils.aggregate_yearly_data(data_type, selected_year)

if pie_df.empty:
    st.warning(f"No data found for **{data_type}** in **{selected_year}**.")
    st.stop()

# --- VISUALIZATION ---
c1, c2 = st.columns(2)

# PIE CHART
with c1:
    st.subheader(f"Total {data_type} Share")
    fig1 = px.pie(pie_df, names='group', values='mwh', hole=0.4)
    fig1.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig1, use_container_width=True)

# LINE CHART
with c2:
    st.subheader("Daily Trend")
    if not line_df.empty:
        # Optional: Filter groups
        all_groups = sorted(line_df['group'].unique())
        sel_groups = st.multiselect("Filter Groups:", all_groups, default=all_groups)
        
        if sel_groups:
            filtered_line = line_df[line_df['group'].isin(sel_groups)]
            fig2 = px.line(filtered_line, x='date', y='daily_mwh', color='group', 
                           labels={'daily_mwh': 'MWh', 'date': 'Date'})
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No timeline data available.")