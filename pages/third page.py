import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Upload CSV
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)

    if 'Month' not in df.columns:
        st.error("CSV must contain a 'Month' column.")
    else:
        # Ensure months are in order as they appear in the CSV
        months = df['Month'].tolist()

        # 1️⃣ Month selection slider (single month or range)
        selected_months = st.select_slider(
            "Select month range",
            options=months,
            value=(months[0], months[0])
        )

        # Filter dataframe based on selected months
        if selected_months[0] == selected_months[1]:
            filtered_df = df[df['Month'] == selected_months[0]]
        else:
            start_idx = months.index(selected_months[0])
            end_idx = months.index(selected_months[1])
            selected_range = months[start_idx:end_idx + 1]
            filtered_df = df[df['Month'].isin(selected_range)]

        # 2️⃣ Column selection
        column_options = ['All columns'] + [col for col in df.columns if col != 'Month']
        selected_column = st.selectbox("Select column to plot", column_options)

        # 3️⃣ Plot
        plt.figure(figsize=(10,5))
        if selected_column == 'All columns':
            for col in filtered_df.columns:
                if col != 'Month':
                    plt.plot(filtered_df['Month'], filtered_df[col], marker='o', label=col)
        else:
            plt.plot(filtered_df['Month'], filtered_df[selected_column], marker='o', label=selected_column)

        plt.title("Data Plot")
        plt.xlabel("Month")
        plt.ylabel("Values")
        plt.grid(True)
        plt.legend()
        st.pyplot(plt)
