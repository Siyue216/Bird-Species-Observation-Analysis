import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# ==========================================
# 1. CONFIGURATION & UI ENHANCEMENTS
# ==========================================
st.set_page_config(page_title="Bird Species Observation Dashboard", page_icon="🐦", layout="wide")

# Custom CSS for spacing and cleaner look
st.markdown("""
<style>
    .css-18e3th9 { padding-top: 1rem; }
    .css-1d391kg { padding-top: 1rem; }
    div.block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. DATABASE CONNECTION & DATA FETCHING
# ==========================================
@st.cache_resource
def init_connection():
    """Initializes and returns a SQLAlchemy Engine connected to PostgreSQL."""
    load_dotenv()
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT')
    db_name = os.environ.get('DB_NAME')
    connection_string = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    engine = create_engine(connection_string)
    return engine

@st.cache_data(ttl=600)
def load_data():
    """Loads bird observation data from the database and performs base preprocessing."""
    engine = init_connection()
    query = """
        SELECT "Admin_Unit_Code", "Sub_Unit_Code", "Site_Name", "Plot_Name", 
               "Location_Type", "Year", "Date", "Start_Time", "End_Time", 
               "Observer", "Visit", "Interval_Length", "ID_Method", 
               "Distance", "Flyover_Observed", "Sex", "Common_Name", 
               "Scientific_Name", "AOU_Code", "AcceptedTSN", "NPSTaxonCode", 
               "PIF_Watchlist_Status", "Regional_Stewardship_Status", 
               "Temperature", "Humidity", "Sky", "Wind", "Disturbance", 
               "Initial_Three_Min_Cnt", "Source_Sheet", "TaxonCode", "Previously_Obs"
        FROM bird_data
    """
    df = pd.read_sql(query, engine)
    
    # Process dates to easily extract Months
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df["Month"] = df["Date"].dt.month_name()
    
    # Convert numerical strings to float for Temperature and Humidity if possible
    df["Temperature"] = pd.to_numeric(df["Temperature"], errors='coerce')
    df["Humidity"] = pd.to_numeric(df["Humidity"], errors='coerce')
    
    return df

with st.spinner("Loading comprehensive dataset from database..."):
    try:
        df = load_data()
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        st.stop()


# ==========================================
# 3. SIDEBAR (FILTERS)
# ==========================================
st.sidebar.title("🛠️ Filter Dashboard")
st.sidebar.markdown("Customize your view by adjusting the filters below:")

# Filter: Month
months_available = []
if "Month" in df.columns:
    months_available = sorted(df["Month"].dropna().unique().tolist())
month_filter = st.sidebar.multiselect("Select Month(s)", options=months_available, default=months_available)

# Filter: Species
species_available = sorted(df["Common_Name"].dropna().unique().tolist())
species_filter = st.sidebar.multiselect("Select Species (Common Name)", options=species_available, default=[])

# Filter: Location_Type
locations_available = ["All"] + sorted(df["Location_Type"].dropna().unique().tolist())
location_filter = st.sidebar.selectbox("Select Location Type", options=locations_available, index=0)

# Filter: Temperature Range
valid_temps = df["Temperature"].dropna()
if not valid_temps.empty:
    min_temp, max_temp = float(valid_temps.min()), float(valid_temps.max())
    temp_filter = st.sidebar.slider("Select Temperature Range", min_value=min_temp, max_value=max_temp, value=(min_temp, max_temp))
else:
    temp_filter = None

# Filter: Sex
sex_available = sorted(df["Sex"].dropna().unique().tolist())
sex_filter = st.sidebar.multiselect("Select Sex", options=sex_available, default=sex_available)

# --- Apply Filters Dynamically ---
df_filtered = df.copy()

if month_filter:
    df_filtered = df_filtered[df_filtered["Month"].isin(month_filter)]

if species_filter:
    df_filtered = df_filtered[df_filtered["Common_Name"].isin(species_filter)]

if location_filter != "All":
    df_filtered = df_filtered[df_filtered["Location_Type"] == location_filter]

if temp_filter is not None:
    # Keep rows where temperature matches the range, OR where temperature is NaN (to avoid losing data missing weather info)
    df_filtered = df_filtered[
        df_filtered["Temperature"].isna() | 
        ((df_filtered["Temperature"] >= temp_filter[0]) & (df_filtered["Temperature"] <= temp_filter[1]))
    ]

if sex_filter:
    df_filtered = df_filtered[df_filtered["Sex"].isin(sex_filter)]


# ==========================================
# 4. MAIN PAGE: TITLE & TABS
# ==========================================
st.title("🐦 Bird Species Observation Dashboard")

# Create the 3 main tabs
tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 In-Depth Analysis", "💡 Key Insights"])


# ==========================================
# TAB 1: OVERVIEW SECTION
# ==========================================
with tab1:
    st.markdown("### Ecological High-Level KPIs")
    
    # KPI Cards
    col1, col2, col3 = st.columns(3)
    kpi_obs = len(df_filtered)
    kpi_species = df_filtered["Scientific_Name"].nunique()
    kpi_plots = df_filtered["Plot_Name"].nunique()
    
    col1.metric("Total Observations", f"{kpi_obs:,}")
    col2.metric("Unique Species", f"{kpi_species:,}")
    col3.metric("Total Locations (Plots)", f"{kpi_plots:,}")
    
    st.markdown("---")
    st.markdown("### 🦉 Species Overview")
    
    top_overall = df_filtered["Common_Name"].value_counts().head(10).reset_index()
    top_overall.columns = ["Species", "Count"]
    fig_overall_sp = px.bar(top_overall, x="Count", y="Species", orientation='h', title="Top 10 Species", color="Count", color_continuous_scale="magma")
    fig_overall_sp.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_overall_sp, use_container_width=True)

    # Raw Data Expander
    with st.expander("🔍 View Raw Observation Data"):
        st.dataframe(df_filtered.head(100))


# ==========================================
# TAB 2: ANALYSIS SECTION
# ==========================================
with tab2:
    # --- TEMPORAL ANALYSIS ---
    st.markdown("### 🕒 Temporal Analysis")
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        if "Start_Time" in df_filtered.columns:
            df_hour = df_filtered.copy()
            # Extract just the first 2 characters (the hour)
            df_hour['Hour_Val'] = pd.to_numeric(df_hour['Start_Time'].astype(str).str[:2], errors='coerce')
            df_hour = df_hour.dropna(subset=['Hour_Val'])
            
            # Map numeric hour to AM/PM string
            def get_am_pm(h):
                h = int(h)
                if h == 0:
                    return "12:00 AM"
                elif h < 12:
                    return f"{h:02d}:00 AM"
                elif h == 12:
                    return "12:00 PM"
                else:
                    return f"{h-12:02d}:00 PM"
            
            df_hour['Hour_Label'] = df_hour['Hour_Val'].apply(get_am_pm)
            
            # Count, sort by the numeric hour to keep chronological order on the axis, then plot
            hour_counts = df_hour.groupby(['Hour_Val', 'Hour_Label']).size().reset_index(name='Observations')
            hour_counts = hour_counts.sort_values("Hour_Val")
            
            fig_hour = px.line(hour_counts, x="Hour_Label", y="Observations", markers=True, title="Observations by Time of Day")
            fig_hour.update_layout(xaxis_title="Time of Day")
            st.plotly_chart(fig_hour, use_container_width=True)
        
    with col_t2:
        if "Month" in df_filtered.columns:
            month_counts = df_filtered["Month"].value_counts().reset_index()
            month_counts.columns = ["Month", "Observations"]
            fig_month = px.bar(month_counts, x="Month", y="Observations", title="Observations per Month", color="Observations", color_continuous_scale="Teal")
            st.plotly_chart(fig_month, use_container_width=True)
        

    if "Date" in df_filtered.columns:
        df_day = df_filtered.copy()
        df_day["DayOfWeek"] = pd.to_datetime(df_day["Date"], errors='coerce').dt.day_name()
        day_counts = df_day["DayOfWeek"].dropna().value_counts().reset_index()
        day_counts.columns = ["DayOfWeek", "Observations"]
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        fig_day = px.bar(day_counts, x="DayOfWeek", y="Observations", title="Observations by Day", category_orders={"DayOfWeek": days_order}, color="DayOfWeek", color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_day, use_container_width=True)
    
    st.markdown("---")
    
    # --- SPATIAL ANALYSIS ---
    st.markdown("### 🗺️ Spatial Analysis")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        loc_counts = df_filtered["Location_Type"].value_counts().reset_index()
        loc_counts.columns = ["Location_Type", "Count"]
        fig_loc = px.bar(loc_counts, x="Location_Type", y="Count", title="Forest vs Grassland Observations", color="Location_Type", color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_loc, use_container_width=True)
        
    with col_s2:
        if "Plot_Name" in df_filtered.columns:
            plot_counts = df_filtered["Plot_Name"].value_counts().head(10).reset_index()
            plot_counts.columns = ["Plot_Name", "Count"]
            fig_plot = px.bar(plot_counts, x="Plot_Name", y="Count", title="Top 10 Plots with Highest Observations", color_discrete_sequence=["coral"])
            fig_plot.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_plot, use_container_width=True)
    st.markdown("---")

    # --- Species Analysis ---
    st.markdown("### 🗺️ Species Analysis")
    
    if "Scientific_Name" in df_filtered.columns:
        st.metric("Total Unique Scientific Species Observed", f"{df_filtered['Scientific_Name'].nunique():,}")
        
        col_sp1, col_sp2 = st.columns(2)
        with col_sp1:
            # Chart 1: Top 10
            top_sci = df_filtered["Scientific_Name"].value_counts().head(10).reset_index()
            top_sci.columns = ["Scientific_Name", "Count"]
            fig_sci = px.bar(top_sci, x="Scientific_Name", y="Count", title="Top 10 Most Frequently Observed Species", color_discrete_sequence=["purple"])
            fig_sci.update_layout(xaxis_tickangle=-45, xaxis_title="Scientific Name", yaxis_title="Observation Count")
            st.plotly_chart(fig_sci, use_container_width=True)
            
        with col_sp2:
            # Chart 2: Rarity
            obs_counts = df_filtered['Scientific_Name'].value_counts()
            bins = [0, 1, 2, 3, 4, 5, 10, 50, 100, float('inf')]
            labels = ['1', '2', '3', '4', '5', '6-10', '11-50', '51-100', '100+']
            binned_freq = pd.cut(obs_counts, bins=bins, labels=labels).value_counts().reindex(labels).fillna(0)
            binned_freq = binned_freq.rename_axis("Observations_Count").reset_index(name="Unique_Species")
            binned_freq["Unique_Species"] = binned_freq["Unique_Species"].astype(int)
            fig_rarity = px.bar(binned_freq, x="Observations_Count", y="Unique_Species", title="Distribution of Species Rarity (How often are species seen?)", color_discrete_sequence=["salmon"], category_orders={"Observations_Count": labels})
            fig_rarity.update_layout(xaxis_tickangle=-45, xaxis_title="Number of Total Observations", yaxis_title="Number of Unique Species")
            fig_rarity.update_traces(texttemplate='%{y}', textposition='outside')
            st.plotly_chart(fig_rarity, use_container_width=True)
            
    if "Sex" in df_filtered.columns:
        sex_counts = df_filtered["Sex"].value_counts().reset_index()
        sex_counts.columns = ["Sex", "Count"]
        fig_sex = px.bar(sex_counts, x="Sex", y="Count", title="Male vs Female vs Unknown Observations", color="Sex", color_discrete_sequence=px.colors.qualitative.Pastel1, category_orders={"Sex": sex_counts["Sex"].tolist()})
        st.plotly_chart(fig_sex, use_container_width=True)
        
    st.markdown("---")
    
    # --- ENVIRONMENTAL ANALYSIS ---
    st.markdown("### 🌤️ Environmental Analysis")
    col_e1, col_e2 = st.columns(2)
    
    with col_e1:
        # Scatter Plot - Dropna to avoid breaking Plotly if some rows lack weather data
        weather_df = df_filtered.dropna(subset=["Temperature", "Humidity"])
        fig_weather = px.scatter(weather_df, x="Temperature", y="Humidity", title="Temperature vs Humidity Distribution", opacity=0.5, color_discrete_sequence=['#ef553b'])
        st.plotly_chart(fig_weather, use_container_width=True)
        
    with col_e2:
        sky_counts = df_filtered["Sky"].value_counts().reset_index()
        sky_counts.columns = ["Sky_Condition", "Observations"]
        fig_sky = px.bar(sky_counts, x="Sky_Condition", y="Observations", title="Weather / Sky Condition Distribution", color="Observations", color_continuous_scale="Blues")
        st.plotly_chart(fig_sky, use_container_width=True)

    col_e3, col_e4 = st.columns(2)
    
    with col_e3:
        wind_counts = df_filtered["Wind"].value_counts().reset_index()
        wind_counts.columns = ["Wind_Condition", "Observations"]
        fig_wind = px.bar(wind_counts, x="Wind_Condition", y="Observations", title="Wind Condition Distribution", color="Observations", color_continuous_scale="Teal")
        st.plotly_chart(fig_wind, use_container_width=True)
        
    with col_e4:
        humid_df = df_filtered.dropna(subset=["Humidity"])
        fig_humid = px.histogram(humid_df, x="Humidity", title="Humidity Distribution", color_discrete_sequence=['cornflowerblue'])
        st.plotly_chart(fig_humid, use_container_width=True)

    col_e5, col_e6 = st.columns(2)
    
    with col_e5:
        disturb_counts = df_filtered["Disturbance"].value_counts().reset_index()
        disturb_counts.columns = ["Disturbance_Level", "Observations"]
        fig_disturb = px.pie(disturb_counts, names="Disturbance_Level", values="Observations", hole=0.3, title="Disturbance Level Distribution", color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_disturb, use_container_width=True)

    with col_e6:
        st.empty() # Placeholder for layout balance

    st.markdown("---")
    
    # --- BEHAVIOR ANALYSIS ---
    st.markdown("### 📏 Behavior Analysis")
    col_b1, col_b2 = st.columns(2)
    
    with col_b1:
        # Bar Chart: ID Method
        id_counts = df_filtered["ID_Method"].value_counts().reset_index()
        id_counts.columns = ["ID_Method", "Count"]
        fig_id = px.bar(id_counts, x="ID_Method", y="Count", title="Identification Method Distribution", color="ID_Method", color_discrete_sequence=px.colors.qualitative.Vivid)
        st.plotly_chart(fig_id, use_container_width=True)
        
    with col_b2:
        fly_counts = df_filtered["Flyover_Observed"].value_counts().reset_index()
        fly_counts.columns = ["Flyover", "Count"]
        # Convert True/False to strings for better chart labels
        fly_counts["Flyover"] = fly_counts["Flyover"].astype(str)
        fig_fly = px.bar(fly_counts, x="Flyover", y="Count", title="Flyover vs Grounded", color="Flyover", color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig_fly, use_container_width=True)

    st.markdown("---")
    
    # --- OBSERVER ANALYSIS ---
    st.markdown("### 👁️ Observer Analysis")
    col_obs1, col_obs2 = st.columns(2)
    
    with col_obs1:
        if "Observer" in df_filtered.columns:
            obs_counts = df_filtered["Observer"].value_counts().head(10).reset_index()
            obs_counts.columns = ["Observer", "Count"]
            fig_obs = px.bar(obs_counts, x="Count", y="Observer", orientation='h', title="Top 10 Active Observers", color="Count", color_continuous_scale="blues")
            fig_obs.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_obs, use_container_width=True)
            
    with col_obs2:
        st.empty()

# ==========================================
# TAB 3: CONSERVATION & KEY INSIGHTS
# ==========================================
with tab3:
    st.markdown("### 🛡️ Conservation Priorities")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if "PIF_Watchlist_Status" in df_filtered.columns:
            pif_counts = df_filtered["PIF_Watchlist_Status"].value_counts().reset_index()
            pif_counts.columns = ["Status", "Count"]
            fig_pif = px.bar(pif_counts, x="Count", y="Status", orientation='h', title="PIF Watchlist Status", color="Count", color_continuous_scale="reds")
            fig_pif.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_pif, use_container_width=True)
            
    with col_c2:
        if "Regional_Stewardship_Status" in df_filtered.columns:
            reg_counts = df_filtered["Regional_Stewardship_Status"].value_counts().reset_index()
            reg_counts.columns = ["Status", "Count"]
            fig_reg = px.bar(reg_counts, x="Status", y="Count", title="Regional Stewardship", color="Status", color_discrete_sequence=px.colors.qualitative.Pastel1)
            st.plotly_chart(fig_reg, use_container_width=True)

    st.markdown("---")

    # Filter for watchlist
    watchlist_df = df_filtered[df_filtered["PIF_Watchlist_Status"] == "True"]
    
    st.metric("Total Watchlist (At-Risk) Sightings", f"{len(watchlist_df):,}")
    
    if not watchlist_df.empty:
        st.markdown("#### At-Risk Species Record")
        watch_counts = watchlist_df["Common_Name"].value_counts().reset_index()
        watch_counts.columns = ["At_Risk_Species", "Observation_Count"]
        st.dataframe(watch_counts, use_container_width=True)
    else:
        st.info("No at-risk species identified within the currently filtered dataset.")
        
    st.markdown("---")
    
    # KEY INSIGHTS SECTION
    st.markdown("### 💡 Key Findings")
    st.markdown("""
    * **Activity Hotspots:** Observations represent substantial biological density, with specific plots acting as extreme ecological hotspots compared to their surroundings.
    * **Species Dominance:** A very small subset of species (such as the Northern Cardinal and Carolina Wren) dominate the total sighting counts, potentially indicating an imbalance in observer detection or extreme population size disparities.
    * **Environmental Impact:** Strong weather correlation implies that clear and partly cloudy skies result in vastly higher yields of sightings compared to poor weather.
    * **At-Risk Presence:** A notable portion of the sightings tracks explicitly protected or endangered species flagged by the PIF Watchlist, spotlighting areas requiring heavy conservation management.
    """)
