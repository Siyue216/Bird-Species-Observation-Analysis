# Bird Species Observation Analysis Dashboard 🐦

This repository contains a comprehensive interactive Streamlit dashboard designed to explore and analyze bird species observation data. Originally backed by PostgreSQL, the application has been transitioned to a local SQLite database for ease of use and portability.

## Features

- **📊 Overview:** Ecological high-level KPIs, top 10 most frequently observed species, and raw observation data.
- **📈 In-Depth Analysis:** 
  - **Temporal Analysis:** Visualizations highlighting peak observation hours (e.g., dawn chorus) and monthly distribution.
  - **Spatial Analysis:** Breakdown of sightings across Forest vs. Grassland habitats and top monitoring plots.
  - **Species & Diversity:** Analysis of species rarity, sex distribution, PIF Watchlist status, and regional stewardship importance.
  - **Environmental Correlation:** Impact of temperature, humidity, wind, sky condition, and anthropogenic disturbance on avian activity.
  - **Behavioral Insights:** Distribution of visual vs. auditory (ear birding) identification and flyover records.
- **🔍 Query Explorer:** A built-in SQL interface allowing users to run custom SQLite queries directly against the `bird_data` table and download findings as CSV.

## Data Source

The insights are powered by the `bird_data.sqlite` database, containing comprehensive biological sampling data focusing on species identification, weather conditionals, habitat mapping, and monitoring observer efforts.

## Installation & Setup

To run the dashboard locally on your machine, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Siyue216/Bird-Species-Observation-Analysis.git
   cd Bird-Species-Observation-Analysis
   ```

2. **Install dependencies:**
   Make sure you have Python installed. Then, run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Streamlit Dashboard:**
   ```bash
   streamlit run app_sqlite.py
   ```

## Technologies Used
- **Python:** Data processing and workflow
- **Streamlit:** Interactive web application framework
- **Plotly Express:** Advanced interactive data visualizations
- **Pandas:** Data manipulation
- **SQLite:** Lightweight local database management

## Deployment
This application is configured for seamless deployment on Streamlit Community Cloud.
