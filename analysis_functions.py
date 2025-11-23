import numpy as np
import pandas as pd
from scipy.signal import spectrogram
from scipy.fft import dct, idct
from statsmodels.tsa.seasonal import STL
from sklearn.neighbors import LocalOutlierFactor
import plotly.graph_objects as go

# --- 1. SNOW DRIFT LOGIC (From Snow_drift.py) ---
def assign_hydro_year(df, date_col='time'):
    """Assigns Hydro Year (July 1st to June 30th)."""
    if not np.issubdtype(df[date_col].dtype, np.datetime64):
         df[date_col] = pd.to_datetime(df[date_col])
    df['hydro_year'] = np.where(df[date_col].dt.month >= 7, df[date_col].dt.year, df[date_col].dt.year - 1)
    return df

def calculate_snow_drift(df):
    """Calculates Snow Transport using Tabler (2003) logic."""
    DENOMINATOR = 233847.0
    # Snowfall if Temp < 1.0C (Approximation used in your script)
    df['swe_mm'] = np.where(df['temperature_2m'] < 1.0, df['precipitation'], 0.0)
    # Potential Transport: u^3.8
    df['Qupot_hourly'] = (df['wind_speed_10m'] ** 3.8 * 3600) / DENOMINATOR
    return df

def compute_seasonal_transport(df_season, T=3000, F=30000, theta=0.5):
    """Aggregates hourly drift into yearly totals."""
    total_swe = df_season['swe_mm'].sum()
    total_qupot = df_season['Qupot_hourly'].sum()
    
    # Limiting Logic
    Qspot = 0.5 * T * total_swe
    Srwe = theta * total_swe
    
    if total_qupot > Qspot:
        Qinf = 0.5 * T * Srwe
        control = "Snowfall Limited"
    else:
        Qinf = total_qupot
        control = "Wind Limited"
        
    Qt = Qinf * (1 - 0.14 ** (F / T))
    return {"Total_Swe_mm": total_swe, "Qt_tonnes_m": Qt / 1000.0, "Control": control}

def get_wind_rose_data(df):
    """Aggregates drift by direction."""
    df['sector_deg'] = (np.round(df['wind_direction_10m'] / 22.5) * 22.5) % 360
    return df.groupby('sector_deg')[['Qupot_hourly']].sum().reset_index()

# --- 2. SPC (Temperature) - FIXED LOGIC ---
def detect_temperature_anomalies_spc(df, freq_cutoff=1500, n_std=3.0):
    """
    freq_cutoff=1500 ensures daily cycle is in Trend, fixing the professor's issue.
    """
    df = df.sort_values('time').reset_index(drop=True)
    temp = df['temperature_2m'].values
    
    coeffs = dct(temp, norm="ortho")
    coeffs_trend = coeffs.copy(); coeffs_trend[freq_cutoff:] = 0
    coeffs_noise = coeffs.copy(); coeffs_noise[:freq_cutoff] = 0
    
    trend = idct(coeffs_trend, norm="ortho")
    noise = idct(coeffs_noise, norm="ortho")
    
    mad = np.median(np.abs(noise - np.median(noise)))
    robust_std = 1.4826 * mad
    
    upper = trend + (n_std * robust_std)
    lower = trend - (n_std * robust_std)
    outliers = (temp > upper) | (temp < lower)
    
    return df['time'], temp, upper, lower, outliers

# --- 3. LOF (Precipitation) ---
def detect_precipitation_anomalies_lof(df, contamination=0.01):
    X = df[['precipitation']].fillna(0).values
    n_neighbors = min(max(5, int(np.sqrt(len(X)))), 50)
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
    y_pred = lof.fit_predict(X)
    return df['time'], df['precipitation'], (y_pred == -1)

# --- 4. STL & SPECTROGRAM (From Old Page 3) ---
def compute_stl(series, period=168, robust=True):
    return STL(series, period=period, robust=robust).fit()

def compute_spectrogram(series, window_length=168, overlap=84):
    f, t, Sxx = spectrogram(series.values, fs=1, nperseg=window_length, noverlap=overlap, window='hann', scaling='density', mode='psd')
    Sxx_dB = 10 * np.log10(Sxx + 1e-9)
    t_axis = series.index[0] + pd.to_timedelta(t, unit="h")
    return f, t_axis, Sxx_dB