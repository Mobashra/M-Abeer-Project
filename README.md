
## IND320 PROJECT - PART 3




This project demonstrates a comprehensive analysis of Norwegian electricity production and meteorological data using Python and Streamlit. It retrieves historical weather reanalysis data for 2021 via the Open-Meteo ERA5 API for the five electricity price areas (Oslo, Kristiansand, Trondheim, Tromsø, and Bergen), storing their coordinates in a structured Pandas DataFrame. The project performs advanced statistical analyses on both weather and production data, including seasonally adjusted outlier detection with high-pass filtering via Direct Cosine Transform, Statistical Process Control (SPC) boundaries, and anomaly detection using Local Outlier Factor (LOF). Production data is further analyzed with Seasonal-Trend decomposition using LOESS (STL) and spectrogram visualizations, with parameters exposed for user control. The Streamlit app integrates these analyses into multiple pages, reordering the workflow to allow selection of price areas first, then performing STL, spectrogram, SPC, and LOF analyses across interactive tabs, with plots, statistics, and summaries displayed for easy interpretation. All plots and functions are wrapped with reusable code, supporting configurable parameters and caching for efficiency, ensuring a responsive and informative interface for examining both weather and electricity production patterns.
