import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ---------- VISUAL POLISH ----------
px.defaults.template = "plotly_white"
px.defaults.color_continuous_scale = "Viridis"

# ---------- DATA LOAD ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
infra_path = os.path.join(BASE_DIR, "isla_coralina_infrastructure.csv")
relief_path = os.path.join(BASE_DIR, "isla_coralina_relief_operations.csv")

@st.cache_data
def load_data():
    infra = pd.read_csv(infra_path)
    relief = pd.read_csv(relief_path, parse_dates=["date"])
    relief["fulfillment_rate"] = relief["quantity_delivered"] / relief["quantity_requested"]
    relief["under_80"] = relief["fulfillment_rate"] < 0.8
    return infra, relief

infra, relief = load_data()

municipalities = sorted(infra["municipality"].unique())
supply_types = sorted(relief["supply_type"].unique())

st.set_page_config(page_title="Isla Coralina Relief Dashboard", layout="wide")

# ---------- TITLE ----------
st.title("Isla Coralina Relief Operations Dashboard")

# Refresh button
if st.button("🔁 Refresh data"):
    infra, relief = load_data()
    st.experimental_rerun()

st.divider()

# ---------- SIDEBAR FILTERS ----------
st.sidebar.header("Global Filters")

muni_filter = st.sidebar.multiselect("Municipality", municipalities, default=municipalities)
supply_filter = st.sidebar.multiselect("Supply type", supply_types, default=supply_types)

date_min, date_max = relief["date"].min(), relief["date"].max()
date_range = st.sidebar.date_input("Date range", [date_min, date_max])

# Apply filters
relief_f = relief[
    (relief["municipality"].isin(muni_filter)) &
    (relief["supply_type"].isin(supply_filter)) &
    (relief["date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))
]
infra_f = infra[infra["municipality"].isin(muni_filter)]

# ---------- TABS ----------
tab_infra, tab_relief = st.tabs(["Infrastructure status", "Relief distribution"])

# ---------- TAB 1: INFRASTRUCTURE ----------
with tab_infra:
    st.subheader("Key infrastructure KPIs")

    total_pop_served = infra_f["population_served"].sum()
    non_op_critical = infra_f[
        (infra_f["operational_status"] == "Non-Operational") &
        (infra_f["facility_type"].isin(["Hospital", "Water Treatment Plant"]))
    ].groupby("municipality")["facility_id"].count()

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Total population served (filtered)", f"{total_pop_served:,}")
    with c2:
        st.write("Non-operational critical facilities by municipality")
        st.dataframe(non_op_critical.rename("count"))

    st.divider()

    st.subheader("Infrastructure status by municipality and type")

    fig1 = px.scatter(
        infra_f,
        x="longitude", y="latitude",
        color="operational_status",
        symbol="facility_type",
        hover_name="facility_name",
        hover_data=["municipality", "damage_severity", "population_served"],
        title="Spatial distribution of infrastructure status"
    )
    st.plotly_chart(fig1, width='stretch')

    fig2 = px.bar(
        infra_f.groupby(["municipality", "operational_status"])["facility_id"].count().reset_index(),
        x="municipality", y="facility_id", color="operational_status",
        title="Facility counts by municipality and status"
    )
    st.plotly_chart(fig2, width='stretch')

    st.caption("Critical infrastructure gaps should guide convoy and repair crew prioritization.")

# ---------- TAB 2: RELIEF ----------
with tab_relief:
    st.subheader("Summary: Weekly Fulfillment Trend")

    summary = relief.groupby(pd.Grouper(key="date", freq="W"))["fulfillment_rate"].mean().reset_index()
    fig_summary = px.line(summary, x="date", y="fulfillment_rate", title="Weekly Fulfillment Rate Trend")
    st.plotly_chart(fig_summary, width='stretch')

    st.divider()

    st.subheader("Relief operations KPIs")

    total_deliveries = len(relief_f)
    avg_delay = relief_f["delivery_delay_hours"].mean()
    pct_under_80 = relief_f["under_80"].mean() * 100

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total deliveries (filtered)", f"{total_deliveries}")
    with c2:
        st.metric("Average delivery delay (hours)", f"{avg_delay:.2f}")
    with c3:
        st.metric("Deliveries < 80% fulfilled", f"{pct_under_80:.1f}%")

    st.divider()

    st.subheader("Fulfillment and delays")

    fig3 = px.box(
        relief_f,
        x="municipality", y="fulfillment_rate",
        title="Fulfillment rate by municipality",
        points="all"
    )
    st.plotly_chart(fig3, width='stretch')

    fig4 = px.box(
        relief_f,
        x="transport_mode", y="delivery_delay_hours",
        color="road_condition",
        title="Delivery delay by transport mode and road condition"
    )
    st.plotly_chart(fig4, width='stretch')

    fig5 = px.line(
        relief_f.groupby("date")["fulfillment_rate"].mean().reset_index(),
        x="date", y="fulfillment_rate",
        title="Daily average fulfillment rate over time"
    )
    st.plotly_chart(fig5, width='stretch')

    fig6 = px.bar(
        relief_f.groupby("supply_type")["fulfillment_rate"].mean().reset_index(),
        x="supply_type", y="fulfillment_rate",
        title="Average fulfillment rate by supply type"
    )
    st.plotly_chart(fig6, width='stretch')

    st.divider()

    # Download button
    st.download_button(
        label="⬇️ Download filtered relief data (CSV)",
        data=relief_f.to_csv(index=False),
        file_name="relief_filtered.csv",
        mime="text/csv"
    )

    st.markdown("""
    **Interpretation:** Under current filters, municipalities with the lowest fulfillment rates and longest delays
    should be prioritized for additional convoys and alternative transport (helicopter/boat), especially where
    road access is limited or weather conditions are severe.
    """)


