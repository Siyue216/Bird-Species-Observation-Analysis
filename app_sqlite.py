import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3

# ==========================================
# 1. CONFIGURATION & UI ENHANCEMENTS
# ==========================================
st.set_page_config(page_title="Bird Species Observation Dashboard (SQLite)", page_icon="🐦", layout="wide")

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
@st.cache_data(ttl=600)
def load_data():
    """Loads bird observation data from the SQLite database and performs base preprocessing."""
    conn = sqlite3.connect('bird_data.sqlite')
    query = """
        SELECT *
        FROM bird_data
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Process dates to easily extract Months
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df["Month"] = df["Date"].dt.month_name()
    
    # Convert numerical strings to float for Temperature and Humidity if possible
    df["Temperature"] = pd.to_numeric(df["Temperature"], errors='coerce')
    df["Humidity"] = pd.to_numeric(df["Humidity"], errors='coerce')
    
    return df

with st.spinner("Loading comprehensive dataset from SQLite database..."):
    try:
        df = load_data()
    except Exception as e:
        st.error(f"Database connection failed. Please ensure 'bird_data.sqlite' exists: {e}")
        st.stop()


# ==========================================
# 3. SIDEBAR (FILTERS)
# ==========================================
st.sidebar.title("🛠️ Filter Dashboard")
st.sidebar.markdown("Customize your view by adjusting the filters below:")

# Filter: Admin Unit Code
admin_available = []
if "Admin_Unit_Code" in df.columns:
    admin_available = sorted(df["Admin_Unit_Code"].dropna().unique().tolist())
admin_filter = st.sidebar.multiselect("Select Admin Unit Code(s)", options=admin_available, default=admin_available)

# Filter: Month
months_available = []
if "Month" in df.columns:
    months_available = sorted(df["Month"].dropna().unique().tolist())
month_filter = st.sidebar.multiselect("Select Month(s)", options=months_available, default=months_available)

# Filter: Species
species_available = []
if "Common_Name" in df.columns:
    species_available = sorted(df["Common_Name"].dropna().unique().tolist())
species_filter = st.sidebar.multiselect("Select Species (Common Name)", options=species_available, default=[])

# Filter: Location_Type
locations_available = ["All"]
if "Location_Type" in df.columns:
    locations_available = ["All"] + sorted(df["Location_Type"].dropna().unique().tolist())
location_filter = st.sidebar.selectbox("Select Location Type", options=locations_available, index=0)

# Filter: Temperature Range
temp_filter = None
if "Temperature" in df.columns:
    valid_temps = df["Temperature"].dropna()
    if not valid_temps.empty:
        min_temp, max_temp = float(valid_temps.min()), float(valid_temps.max())
        if min_temp < max_temp:
            temp_filter = st.sidebar.slider("Select Temperature Range", min_value=min_temp, max_value=max_temp, value=(min_temp, max_temp))

# Filter: Sex
sex_available = []
if "Sex" in df.columns:
    sex_available = sorted(df["Sex"].dropna().unique().tolist())
sex_filter = st.sidebar.multiselect("Select Sex", options=sex_available, default=sex_available)

# --- Apply Filters Dynamically ---
df_filtered = df.copy()

if admin_filter and "Admin_Unit_Code" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["Admin_Unit_Code"].isin(admin_filter)]

if month_filter and "Month" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["Month"].isin(month_filter)]

if species_filter and "Common_Name" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["Common_Name"].isin(species_filter)]

if location_filter != "All" and "Location_Type" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["Location_Type"] == location_filter]

if temp_filter is not None and "Temperature" in df_filtered.columns:
    # Keep rows where temperature matches the range, OR where temperature is NaN (to avoid losing data missing weather info)
    df_filtered = df_filtered[
        df_filtered["Temperature"].isna() | 
        ((df_filtered["Temperature"] >= temp_filter[0]) & (df_filtered["Temperature"] <= temp_filter[1]))
    ]

if sex_filter and "Sex" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["Sex"].isin(sex_filter)]


# ==========================================
# 4. MAIN PAGE: TITLE & TABS
# ==========================================
st.title("🐦 Bird Species Observation Dashboard (SQLite Version)")

# Create the 4 main tabs
tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 In-Depth Analysis", "🔍 Query Explorer"])


# ==========================================
# TAB 1: OVERVIEW SECTION
# ==========================================
with tab1:
    st.markdown("### Ecological High-Level KPIs")
    
    # KPI Cards
    col1, col2, col3 = st.columns(3)
    kpi_obs = len(df_filtered)
    kpi_species = df_filtered["Scientific_Name"].nunique() if "Scientific_Name" in df_filtered.columns else 0
    kpi_plots = df_filtered["Plot_Name"].nunique() if "Plot_Name" in df_filtered.columns else 0
    
    col1.metric("Total Observations", f"{kpi_obs:,}")
    col2.metric("Unique Species", f"{kpi_species:,}")
    col3.metric("Total Locations (Plots)", f"{kpi_plots:,}")
    
    st.markdown("---")
    st.markdown("### 🦉 Species Overview")
    
    if "Common_Name" in df_filtered.columns:
        top_overall = df_filtered["Common_Name"].value_counts().head(10).reset_index()
        top_overall.columns = ["Species", "Count"]
        fig_overall_sp = px.bar(top_overall, x="Count", y="Species", orientation='h', title="Top 10 Species", color="Count", color_continuous_scale="magma")
        fig_overall_sp.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_overall_sp, use_container_width=True)
        st.info("💡 Insight: The top 10 most frequently observed species account for a significant portion of all sightings. Dominant species such as the Northern Cardinal and Carolina Wren thrive in these monitored habitats, likely due to high adaptability, territorial vocalizations making them easier to detect, or stable food sources within the plots.")

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
            st.info("💡 Insight: There is a sharp spike in observations during the early morning hours (commonly known as the dawn chorus). Avian activity peaks as birds actively forage and sing to establish territory immediately after sunrise. Observation efficiency steeply declines towards midday as temperatures rise and birds seek shelter.")
        
    with col_t2:
        if "Month" in df_filtered.columns:
            month_counts = df_filtered["Month"].value_counts().reset_index()
            month_counts.columns = ["Month", "Observations"]
            fig_month = px.bar(month_counts, x="Month", y="Observations", title="Observations per Month", color="Observations", color_continuous_scale="Teal")
            st.plotly_chart(fig_month, use_container_width=True)
            st.info("💡 Insight: Observations are overwhelmingly clustered around May and early summer. This accurately reflects peak spring migration and breeding seasons when birds are most active, highly vocal, and passing through various ecological corridors in large numbers.")
        

    if "Date" in df_filtered.columns:
        df_day = df_filtered.copy()
        df_day["DayOfWeek"] = pd.to_datetime(df_day["Date"], errors='coerce').dt.day_name()
        day_counts = df_day["DayOfWeek"].dropna().value_counts().reset_index()
        day_counts.columns = ["DayOfWeek", "Observations"]
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        fig_day = px.bar(day_counts, x="DayOfWeek", y="Observations", title="Observations by Day", category_orders={"DayOfWeek": days_order}, color="DayOfWeek", color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_day, use_container_width=True)
        st.info("💡 Insight: The distribution of observations across the days of the week is relatively varied. Fluctuations here are more indicative of the scheduling availability of volunteer observers or field technicians rather than actual biological phenomena.")
    
    st.markdown("---")
    
    # --- SPATIAL ANALYSIS ---
    st.markdown("### 🗺️ Spatial Analysis")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if "Location_Type" in df_filtered.columns:
            loc_counts = df_filtered["Location_Type"].value_counts().reset_index()
            loc_counts.columns = ["Location_Type", "Count"]
            fig_loc = px.bar(loc_counts, x="Location_Type", y="Count", title="Forest vs Grassland Observations", color="Location_Type", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_loc, use_container_width=True)
            st.info("💡 Insight: Forest habitats yield a consistently higher volume of observations compared to grasslands. This implies that the forested areas in this dataset either offer richer biodiversity, support larger populations, or have been surveyed more intensively by the monitoring teams.")
        
    with col_s2:
        if "Plot_Name" in df_filtered.columns:
            plot_counts = df_filtered["Plot_Name"].value_counts().head(10).reset_index()
            plot_counts.columns = ["Plot_Name", "Count"]
            fig_plot = px.bar(plot_counts, x="Plot_Name", y="Count", title="Top 10 Plots with Highest Observations", color_discrete_sequence=["coral"])
            fig_plot.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_plot, use_container_width=True)
            st.info("💡 Insight: A distinct subset of monitoring plots drives the vast majority of the data. Identifying these ecological hotspots allows conservationists to prioritize funding and protective measures for these specific high-density habitats.")
    st.markdown("---")

    # --- Species Analysis ---
    st.markdown("### 🗺️ Species Analysis")
    
    if "Scientific_Name" in df_filtered.columns:
        col_sp1, col_sp2 = st.columns(2)
        with col_sp1:
            # Chart 1: Top 10
            top_sci = df_filtered["Scientific_Name"].value_counts().head(10).reset_index()
            top_sci.columns = ["Scientific_Name", "Count"]
            fig_sci = px.bar(top_sci, x="Scientific_Name", y="Count", title="Top 10 Most Frequently Observed Species", color_discrete_sequence=["purple"])
            fig_sci.update_layout(xaxis_tickangle=-45, xaxis_title="Scientific Name", yaxis_title="Observation Count")
            st.plotly_chart(fig_sci, use_container_width=True)
            st.info("💡 Insight: Taxonomically, Cardinalis cardinalis is the most consistently recorded species. This visual corroborates the common name chart, demonstrating how widespread and successful generalist species are within these ecological niches.")
            
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
            st.info("💡 Insight: The rarity distribution highlights a classic 'long tail' curve in biological sampling. While a few species are seen thousands of times, the vast majority of unique species are documented fewer than 5 times, emphasizing the hidden, fragile biodiversity of the region.")
            
    if "Sex" in df_filtered.columns:
        sex_counts = df_filtered["Sex"].value_counts().reset_index()
        sex_counts.columns = ["Sex", "Count"]
        fig_sex = px.bar(sex_counts, x="Sex", y="Count", title="Male vs Female vs Unknown Observations", color="Sex", color_discrete_sequence=px.colors.qualitative.Pastel1, category_orders={"Sex": sex_counts["Sex"].tolist()})
        st.plotly_chart(fig_sex, use_container_width=True)
        st.info("💡 Insight: Among identified sexes, males are overwhelmingly represented. Male birds are generally more conspicuous due to bright plumage and territorial singing, introducing a natural detection bias into the monitoring data.")
        
    st.markdown("---")
    
    # --- ENVIRONMENTAL ANALYSIS ---
    st.markdown("### 🌤️ Environmental Analysis")
    col_e1, col_e2 = st.columns(2)
    
    with col_e1:
        if "Temperature" in df_filtered.columns and "Humidity" in df_filtered.columns:
            # Scatter Plot - Dropna to avoid breaking Plotly if some rows lack weather data
            weather_df = df_filtered.dropna(subset=["Temperature", "Humidity"])
            if not weather_df.empty:
                fig_weather = px.scatter(weather_df, x="Temperature", y="Humidity", title="Temperature vs Humidity Distribution", opacity=0.5, color_discrete_sequence=['#ef553b'])
                st.plotly_chart(fig_weather, use_container_width=True)
                st.info("💡 Insight: Sightings are densely concentrated in moderate temperatures (15-25°C) with humidity levels clustering heavily between 60-90%. Extreme heat or cold suppresses both bird activity and surveyor presence.")
        
    with col_e2:
        if "Sky" in df_filtered.columns:
            sky_counts = df_filtered["Sky"].value_counts().reset_index()
            sky_counts.columns = ["Sky_Condition", "Observations"]
            fig_sky = px.bar(sky_counts, x="Sky_Condition", y="Observations", title="Weather / Sky Condition Distribution", color="Observations", color_continuous_scale="Blues")
            st.plotly_chart(fig_sky, use_container_width=True)
            st.info("💡 Insight: Clear or partly cloudy conditions correlate heavily with the highest observation frequencies. Unobstructed skies improve visibility and correspond with favorable foraging weather, whereas heavy rain or overcast skies suppress avian activity.")

    col_e3, col_e4 = st.columns(2)
    
    with col_e3:
        if "Wind" in df_filtered.columns:
            wind_counts = df_filtered["Wind"].value_counts().reset_index()
            wind_counts.columns = ["Wind_Condition", "Observations"]
            fig_wind = px.bar(wind_counts, x="Wind_Condition", y="Observations", title="Wind Condition Distribution", color="Observations", color_continuous_scale="Teal")
            st.plotly_chart(fig_wind, use_container_width=True)
            st.info("💡 Insight: Calm, low-wind conditions are vastly preferred. High wind directly suppresses bird movement, forces birds to seek deep cover, and profoundly hinders acoustic detection (ear birding), drastically lowering identification rates.")
        
    with col_e4:
        if "Humidity" in df_filtered.columns:
            humid_df = df_filtered.dropna(subset=["Humidity"])
            if not humid_df.empty:
                fig_humid = px.histogram(humid_df, x="Humidity", title="Humidity Distribution", color_discrete_sequence=['cornflowerblue'])
                st.plotly_chart(fig_humid, use_container_width=True)
                st.info("💡 Insight: Most sightings correspond to periods of relatively high humidity, which coincides naturally with the early morning dawn chorus when temperatures are cool and dew is present.")

    col_e5, col_e6 = st.columns(2)
    
    with col_e5:
        if "Disturbance" in df_filtered.columns:
            disturb_counts = df_filtered["Disturbance"].value_counts().reset_index()
            disturb_counts.columns = ["Disturbance_Level", "Observations"]
            fig_disturb = px.pie(disturb_counts, names="Disturbance_Level", values="Observations", hole=0.3, title="Disturbance Level Distribution", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_disturb, use_container_width=True)
            st.info("💡 Insight: The overwhelmingly high proportion of 'Light' or 'None' disturbance records confirms that these habitats are relatively pristine and that birds are highly sensitive to significant anthropogenic noise or physical disruption.")

    with col_e6:
        st.empty() # Placeholder for layout balance

    st.markdown("---")
    
    # --- BEHAVIOR ANALYSIS ---
    st.markdown("### 📏 Behavior Analysis")
    col_b1, col_b2 = st.columns(2)
    
    with col_b1:
        # Bar Chart: ID Method
        if "ID_Method" in df_filtered.columns:
            id_counts = df_filtered["ID_Method"].value_counts().reset_index()
            id_counts.columns = ["ID_Method", "Count"]
            fig_id = px.bar(id_counts, x="ID_Method", y="Count", title="Identification Method Distribution", color="ID_Method", color_discrete_sequence=px.colors.qualitative.Vivid)
            st.plotly_chart(fig_id, use_container_width=True)
            st.info("💡 Insight: Auditory identification (Song/Call) far outweighs pure visual confirmation. In dense forest habitats, observers heavily rely on acoustic signatures to catalog species that remain obscured by foliage, showcasing the essential nature of ear birding.")
        
    with col_b2:
        if "Flyover_Observed" in df_filtered.columns:
            fly_counts = df_filtered["Flyover_Observed"].value_counts().reset_index()
            fly_counts.columns = ["Flyover", "Count"]
            # Convert True/False to strings for better chart labels
            fly_counts["Flyover"] = fly_counts["Flyover"].astype(str)
            fig_fly = px.bar(fly_counts, x="Flyover", y="Count", title="Flyover vs Grounded", color="Flyover", color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig_fly, use_container_width=True)
            st.info("💡 Insight: The vast majority of birds recorded were actively utilizing the study habitats (listed as False for flyover). This indicates that the monitored plots serve as crucial foraging or nesting grounds rather than mere transitional airspace.")

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
            st.info("💡 Insight: A concentrated group of incredibly active observers contributes an outsized portion of the dataset. Distributing effort and recruiting more trained observers could help reduce individual bias and expand geographical coverage.")
            
    with col_obs2:
        st.empty()

# CONSERVATION & KEY INSIGHTS

    st.markdown("### 🛡️ Conservation Priorities")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if "PIF_Watchlist_Status" in df_filtered.columns:
            pif_counts = df_filtered["PIF_Watchlist_Status"].value_counts().reset_index()
            pif_counts.columns = ["Status", "Count"]
            fig_pif = px.bar(pif_counts, x="Count", y="Status", orientation='h', title="PIF Watchlist Status", color="Count", color_continuous_scale="reds")
            fig_pif.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_pif, use_container_width=True)
            st.info("💡 Insight: Noteworthy volumes of observations belong to species flagged on the PIF (Partners in Flight) Watchlist. This underscores the profound conservation value of these monitored plots as vital refuges for at-risk species.")
            
    with col_c2:
        if "Regional_Stewardship_Status" in df_filtered.columns:
            reg_counts = df_filtered["Regional_Stewardship_Status"].value_counts().reset_index()
            reg_counts.columns = ["Status", "Count"]
            fig_reg = px.bar(reg_counts, x="Status", y="Count", title="Regional Stewardship", color="Status", color_discrete_sequence=px.colors.qualitative.Pastel1)
            st.plotly_chart(fig_reg, use_container_width=True)
            st.info("💡 Insight: Regional Stewardship species have significant localized records. Prioritizing management of these specific habitats ensures that regionally important species do not face localized extinction and maintain stable demographics.")

    st.markdown("---")

    # # Filter for watchlist
    # if "PIF_Watchlist_Status" in df_filtered.columns:
    #     watchlist_df = df_filtered[df_filtered["PIF_Watchlist_Status"] == "True"]
        
    #     st.metric("Total Watchlist (At-Risk) Sightings", f"{len(watchlist_df):,}")
        
    #     if not watchlist_df.empty:
    #         st.markdown("#### At-Risk Species Record")
    #         watch_counts = watchlist_df["Common_Name"].value_counts().reset_index()
    #         watch_counts.columns = ["At_Risk_Species", "Observation_Count"]
    #         st.dataframe(watch_counts, use_container_width=True)
    #     else:
    #         st.info("No at-risk species identified within the currently filtered dataset.")
            
    #     st.markdown("---")
    
    # # KEY INSIGHTS SECTION
    # st.markdown("### 💡 Key Findings")
    # st.markdown("""
    # * **Activity Hotspots:** Observations represent substantial biological density, with specific plots acting as extreme ecological hotspots compared to their surroundings.
    # * **Species Dominance:** A very small subset of species (such as the Northern Cardinal and Carolina Wren) dominate the total sighting counts, potentially indicating an imbalance in observer detection or extreme population size disparities.
    # * **Environmental Impact:** Strong weather correlation implies that clear and partly cloudy skies result in vastly higher yields of sightings compared to poor weather.
    # * **At-Risk Presence:** A notable portion of the sightings tracks explicitly protected or endangered species flagged by the PIF Watchlist, spotlighting areas requiring heavy conservation management.
    # """)

# ==========================================
# TAB 3: QUERY EXPLORER
# ==========================================
with tab3:
    st.markdown("### 🔍 SQL Query Explorer")
    st.markdown("Extract specific data using raw SQL queries targeting the `bird_data` table.")
    
    query_input = st.text_area("Enter your SQL query below:", value="SELECT * FROM bird_data LIMIT 10;", height=150)
    
    if st.button("Run Query"):
        with st.spinner("Executing query..."):
            try:
                conn_query = sqlite3.connect('bird_data.sqlite')
                query_df = pd.read_sql(query_input, conn_query)
                conn_query.close()
                
                st.success(f"Query executed successfully! {len(query_df)} rows returned.")
                st.dataframe(query_df, use_container_width=True)
                
                csv = query_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name='extracted_data.csv',
                    mime='text/csv',
                )
            except Exception as e:
                st.error(f"Error executing query: {e}")
