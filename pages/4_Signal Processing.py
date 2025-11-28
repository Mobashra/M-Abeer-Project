import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import utils
import analysis_functions as af

st.set_page_config(page_title="Signal Processing", page_icon="📡", layout="wide")
st.title("📡 Signal Processing: STL & Frequency")

if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

# --- SIDEBAR CONFIG ---
with st.sidebar:
    st.header("Data Source")
    year = st.selectbox("Year", [2021, 2022, 2023], index=0)
    data_type = st.radio("Type", ["Production", "Consumption"])
    
    st.divider()
    st.header("Parameters")
    # STL Params
    period = st.number_input("STL Period (Hours)", value=168, help="168 = Weekly seasonality")
    seasonal = st.number_input("Seasonal Smoother", value=13, step=2)
    trend = st.number_input("Trend Smoother", value=169, step=2)
    
    # Spectrogram Params
    win_len = st.slider("Window Length", 50, 500, 256)

# --- LOAD DATA ---
df = utils.load_yearly_data(data_type, year)
if df.empty: st.stop()

# Filter Area
df_area = df[df['price_area'] == st.session_state["selected_price_area"]]
groups = sorted(df_area['group'].unique())
selected_group = st.selectbox("Select Energy Group", groups)

# Prepare Series
series = df_area[df_area['group'] == selected_group].set_index('date')['mwh'].sort_index().asfreq('h').interpolate()

# --- TABS ---
tab_stl, tab_spec = st.tabs(["STL Decomposition", "Spectrogram"])

with tab_stl:
    if st.button("Run STL Decomposition"):
        with st.spinner("Decomposing..."):
            try:
                res = af.compute_stl(series, period=period, seasonal=seasonal, trend=trend)
                
                # Create 4-row subplot
                fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                                    subplot_titles=["Observed", "Trend", "Seasonal", "Residuals"])
                
                fig.add_trace(go.Scatter(x=res.observed.index, y=res.observed, name="Observed"), row=1, col=1)
                fig.add_trace(go.Scatter(x=res.trend.index, y=res.trend, name="Trend", line=dict(color='orange')), row=2, col=1)
                fig.add_trace(go.Scatter(x=res.seasonal.index, y=res.seasonal, name="Seasonal", line=dict(color='green')), row=3, col=1)
                fig.add_trace(go.Scatter(x=res.resid.index, y=res.resid, name="Resid", line=dict(width=0.5, color='gray')), row=4, col=1)
                
                fig.update_layout(height=800, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"STL Error: {e}")

with tab_spec:
    if st.button("Generate Spectrogram"):
        try:
            f, t, Sxx = af.compute_spectrogram(series, window_length=win_len)
            fig = go.Figure(data=go.Heatmap(z=Sxx, x=t, y=f, colorscale='Jet'))
            fig.update_layout(
                title="Frequency Intensity over Time",
                yaxis_title="Frequency (Hz)", xaxis_title="Time",
                yaxis_range=[0, 0.1]
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Spectrogram Error: {e}")