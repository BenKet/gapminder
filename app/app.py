import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import re

@st.cache_data
def load_and_process_data():
    # Load the CSV files
    life_expectancy_df = pd.read_csv('data/lex.csv')
    population_df = pd.read_csv('data/pop.csv')
    gni_per_capita_df = pd.read_csv('data/ny_gnp_pcap_pp_cd.csv')

    # Forward fill missing values
    life_expectancy_df.ffill(inplace=True)
    population_df.ffill(inplace=True)
    gni_per_capita_df.ffill(inplace=True)

    # Transform to tidy data format
    def transform_to_tidy(df, kpi_name):
        df = df.set_index(df.columns[0]).rename_axis('country')
        df.columns.name = 'year'
        df = df.reset_index().melt(id_vars='country', var_name='year', value_name=kpi_name)
        return df
    

    def convert_population(pop_str):
        abbrev_to_multiplier = {
            'k': 1000,
            'M': 1000000,
            'B': 1000000000
        }

        match = re.match(r'^(\d+\.?\d*)([kMB]?)$', pop_str)
        if match:
            # Extract numeric part and abbreviation
            numeric_part = float(match.group(1))
            abbreviation = match.group(2)

            # Check if abbreviation exists in the dictionary
            if abbreviation in abbrev_to_multiplier:
                multiplier = abbrev_to_multiplier[abbreviation]
                return int(numeric_part * multiplier)
            else:
                # If no abbreviation, return the numeric part as it is
                return int(numeric_part)
        else:
            # Return None if the string does not match the expected format
            return None

    life_expectancy_df = transform_to_tidy(life_expectancy_df, 'life_expectancy')
    population_df = transform_to_tidy(population_df, 'population')
    gni_per_capita_df = transform_to_tidy(gni_per_capita_df, 'gni_per_capita')

    # Convert population values to numeric format
    population_df['population'] = population_df['population'].apply(convert_population)

    # Convert year to integer and other columns to numeric
    for df in [life_expectancy_df, population_df, gni_per_capita_df]:
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df.iloc[:, 2] = pd.to_numeric(df.iloc[:, 2], errors='coerce')

    # Merge the dataframes
    merged_df = life_expectancy_df.merge(population_df, on=['country', 'year'])
    merged_df = merged_df.merge(gni_per_capita_df, on=['country', 'year'])

    # Forward fill any remaining NaNs after type conversion
    merged_df.ffill(inplace=True)

    return merged_df

# Load and process data
df = load_and_process_data()

# Streamlit app
st.title('Data Visualization Dashboard')

# Year slider
years = df['year'].unique()
year = st.slider('Select year', int(years.min()), int(years.max()), int(years.min()))

# Country multiselect
countries = df['country'].unique()
selected_countries = st.multiselect('Select countries', countries, default=countries)

# Filter dataframe based on selections
filtered_df = df[(df['year'] == year) & (df['country'].isin(selected_countries))]

# Bubble chart
chart = alt.Chart(filtered_df).mark_circle().encode(
    x=alt.X('gni_per_capita:Q', scale=alt.Scale(type='log', domain=[1, df['gni_per_capita'].max()])),
    y='life_expectancy:Q',
    size=alt.Size('population:Q', scale=alt.Scale(range=[10, 1000])),
    color='country:N',
    tooltip=['country', 'year', 'gni_per_capita', 'life_expectancy', 'population']
).properties(
    width=800,
    height=600
).interactive()

st.altair_chart(chart, use_container_width=True)
