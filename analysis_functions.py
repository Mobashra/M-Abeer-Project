import numpy as np
import pandas as pd
from scipy.signal import spectrogram
from scipy.fft import dct, idct
from statsmodels.tsa.seasonal import STL
from sklearn.neighbors import LocalOutlierFactor
import plotly.graph_objects as go

# ==========================================
# 1. SNOW DRIFT LOGIC (Tabler 2003)
# ==========================================

def assign_hydro_year(df, date_col='time'):
    """
    Assigns Hydro Year (July 1st to June 30th).
    """
    # Ensure column is datetime
    if not np.issubdtype(df[date_col].dtype, np.datetime64):
         df[date_col] = pd.to_datetime(df[date_col])
         
    df['hydro_year'] = np.where(
        df[date_col].dt.month >= 7,
        df[date_col].dt.year,
        df[date_col].dt.year - 1
    )
    return df

def calculate_snow_drift(df):
    """
    Calculates hourly snow transport components based on Tabler (2003).
    """
    DENOMINATOR = 233847.0 
    
    # Snow is defined as Precip when Temp < 1.0°C
    df['is_snow'] = df['temperature_2m'] < 1.0
    df['swe_mm'] = np.where(df['is_snow'], df['precipitation'], 0.0)
    
    # Potential Transport = Wind Speed ^ 3.8
    u = df['wind_speed_10m']
    df['Qupot_hourly'] = (u ** 3.8 * 3600) / DENOMINATOR
    
    return df

def compute_seasonal_transport(df_season, T=3000, F=30000, theta=0.5):
    """
    Aggregates hourly data into a Seasonal Total (Qt).
    """
    total_swe = df_season['swe_mm'].sum()
    total_qupot = df_season['Qupot_hourly'].sum()
    
    # Calculate Limits
    Qspot = 0.5 * T * total_swe
    Srwe = theta * total_swe
    
    # Determine Controlling Process
    if total_qupot > Qspot:
        Qinf = 0.5 * T * Srwe
        control = "Snowfall Limited"
    else:
        Qinf = total_qupot
        control = "Wind Limited"
        
    Qt = Qinf * (1 - 0.14 ** (F / T))
    
    return {
        "Total_Swe_mm": total_swe,
        "Total_Qupot": total_qupot,
        "Qt_kg_m": Qt,
        "Qt_tonnes_m": Qt / 1000.0,
        "Control_Type": control
    }

def compute_fence_height(Qt_kg_m, fence_type):
    """
    Calculates required fence height (H).
    """
    Qt_tonnes = Qt_kg_m / 1000.0
    factors = {"Wyoming": 8.5, "Slat-and-wire": 7.7, "Solid": 2.9}
    
    factor = factors.get(fence_type, 8.5)
    
    if Qt_tonnes <= 0: return 0.0
    
    H = (Qt_tonnes / factor) ** (1 / 2.2)
    return H

def get_wind_rose_data(df):
    """Aggregates drift potential by wind direction."""
    # Bin into 16 sectors
    df['sector_deg'] = (np.round(df['wind_direction_10m'] / 22.5) * 22.5) % 360
    rose_data = df.groupby('sector_deg')[['Qupot_hourly']].sum().reset_index()
    return rose_data

# ==========================================
# 2. SPC (Temperature) - FIXED PHYSICS
# ==========================================

def detect_temperature_anomalies_spc(df, freq_cutoff=1500, n_std=3.0):
    """
    Detects temperature outliers using DCT.
    freq_cutoff=1500 ensures daily cycle is in Trend (Physics Fix).
    """
    df = df.sort_values('time').reset_index(drop=True)
    temp = df['temperature_2m'].values
    
    coeffs = dct(temp, norm="ortho")
    
    # Trend (Low Freq)
    coeffs_trend = coeffs.copy(); coeffs_trend[freq_cutoff:] = 0
    trend = idct(coeffs_trend, norm="ortho")
    
    # Noise (High Freq)
    coeffs_noise = coeffs.copy(); coeffs_noise[:freq_cutoff] = 0
    noise = idct(coeffs_noise, norm="ortho")
    
    # Robust Stats
    mad = np.median(np.abs(noise - np.median(noise)))
    robust_std = 1.4826 * mad
    
    upper = trend + (n_std * robust_std)
    lower = trend - (n_std * robust_std)

    outliers = (temp > upper) | (temp < lower)
    return df['time'], temp, upper, lower, outliers

# ==========================================
# 3. LOF (Precipitation)
# ==========================================

def detect_precipitation_anomalies_lof(df, contamination=0.01):
    """Detects rain anomalies using Local Outlier Factor."""
    df = df.sort_values('time').reset_index(drop=True)
    X = df[['precipitation']].fillna(0).values
    
    # Dynamic neighbors based on data size
    n_neighbors = min(max(5, int(np.sqrt(len(X)))), 50)
    
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
    y_pred = lof.fit_predict(X)
    outliers = (y_pred == -1)
    
    return df['time'], df['precipitation'], outliers

# ==========================================
# 4. STL & SPECTROGRAM
# ==========================================

def compute_stl(series, period=168, seasonal=13, trend=None, robust=True):
    """
    Performs STL decomposition.
    Ensures parameters are ODD integers (Required by Statsmodels).
    """
    if seasonal % 2 == 0: seasonal += 1
    
    if trend is not None:
        trend = int(trend)
        if trend % 2 == 0: trend += 1
    
    stl = STL(series, period=period, seasonal=seasonal, trend=trend, robust=robust)
    return stl.fit()

def compute_spectrogram(series, window_length=168, overlap=84):
    """Computes Power Spectrogram in dB."""
    f, t, Sxx = spectrogram(
        series.values, 
        fs=1, 
        nperseg=window_length, 
        noverlap=overlap, 
        window='hann', 
        scaling='density', 
        mode='psd'
    )
    Sxx_dB = 10 * np.log10(Sxx + 1e-9)
    t_axis = series.index[0] + pd.to_timedelta(t, unit="h")
    return f, t_axis, Sxx_dB