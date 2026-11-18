"""Heat Shield - Streamlit app (Week 3 skeleton).

Run it:  streamlit run app.py
Three tabs: 1 Site survey, 2 Upload, 3 Results.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from acclimatization import SOURCE as ACCLIM_SOURCE
from acclimatization import calendar
from loaders import RosterError, load_roster
from triggers import daily_triggers, load_rules, rule_for_state
from weather import WeatherError, load_station_csv, weather_for_zip
from workrest import NIOSH_URL, OREGON_URL, add_work_rest, band_table

ROOT = Path(__file__).resolve().parent
NOT_LEGAL_ADVICE = ("Heat Shield helps you plan for heat safety. It does not replace a licensed "
                    "safety professional or an attorney.")
PRIVACY = ("Privacy: Heat Shield never asks for names. Files you upload are read in memory "
           "and thrown away when you close this page. Nothing is saved.")

st.set_page_config(page_title="Heat Shield", page_icon="☀️", layout="wide")
st.title("☀️ Heat Shield")
st.caption("A heat safety plan for small employers: water, rest, shade, and a slow start for new workers.")
st.info(PRIVACY)

rules, rules_date = load_rules()
survey_tab, upload_tab, results_tab = st.tabs(["1. Site survey", "2. Upload", "3. Results"])

# ---------------- 1. Site survey ----------------
with survey_tab:
    st.subheader("Tell us about the work site")
    col1, col2 = st.columns(2)
    with col1:
        state = st.selectbox("State", ["MA", "CA", "WA", "OR", "MD", "Other"])
        setting = st.radio("Where is the work done?", ["Outdoors", "Indoors", "Both"], horizontal=True)
        industry = st.selectbox("Industry", ["Landscaping", "Roofing", "Construction", "Warehouse / moving",
                                             "Restaurant kitchen", "Car wash", "Other"])
        sun_label = st.selectbox("During the day, the work is mostly in...",
                                 ["Full sun", "Partly cloudy / some shade", "Shade or indoors"])
        workload_label = st.selectbox(
            "How hard is the work?",
            ["Light (sitting or standing, little arm work)",
             "Moderate (walking, pushing light carts, raking)",
             "Heavy (digging, carrying heavy loads, roofing)"], index=1)
        clothing_label = st.selectbox("What do workers wear?",
                                      ["Normal work clothes", "Non-breathable coveralls or chemical suit"])
        heat_sources = st.multiselect("Indoor heat sources", ["Ovens / grills", "Machinery", "Dryers", "None"])
    with col2:
        shade = st.selectbox("Shade for breaks", ["Natural (trees)", "Structure (tent, building)", "None"])
        water_minutes = st.number_input("Minutes to walk to drinking water", 0, 60, 2)
        crew_size = st.number_input("Crew size", 1, 500, 8)
        shift_hours = st.number_input("Normal shift length (hours)", 4, 14, 8)
        languages = st.multiselect("Languages workers speak",
                                   ["English", "Spanish", "Portuguese", "Haitian Creole", "Vietnamese", "Other"],
                                   default=["English", "Spanish"])
        new_workers = st.radio("Any new or returning workers this season?", ["Yes", "No", "Not sure"],
                               horizontal=True)
        er = st.text_input("Nearest emergency room (hospital name)", placeholder="e.g. Boston Medical Center")

    # Turn the answers into the words the engine uses
    sun = {"Full sun": "full", "Partly cloudy / some shade": "partly", "Shade or indoors": "none"}[sun_label]
    workload = workload_label.split()[0].lower()
    clothing = "normal" if clothing_label == "Normal work clothes" else "chemical_suit"

    if shade == "None":
        st.warning("Every rule in Heat Shield requires shade or a cool-down area once the initial trigger is reached.")
    if water_minutes > 5:
        st.warning("Water should be close by. More than a few minutes away means workers drink less.")

# ---------------- 2. Upload ----------------
with upload_tab:
    st.subheader("Worker roster")
    st.write("One row per worker: `worker_id` (a code like W001, never a name), `site`, `job`, "
             "`start_date`, and `return_date` if they were away a week or more.")
    roster_file = st.file_uploader("Upload roster (.csv or .xlsx)", type=["csv", "xlsx"])
    use_sample_roster = st.checkbox("Use the sample roster (25 made-up workers)", value=roster_file is None)

    st.subheader("Weather")
    weather_choice = st.radio("Weather source", [
        "Sample: real Boston heat wave, June 21-27, 2025",
        "7-day forecast for a ZIP code",
        "Upload a weather station CSV"])
    zip_code = station_file = None
    if weather_choice.startswith("7-day"):
        zip_code = st.text_input("ZIP code", "02125")
    elif weather_choice.startswith("Upload"):
        station_file = st.file_uploader("Station CSV (NOAA, or columns time, temp_f, rh)", type=["csv"])


@st.cache_data(ttl=3600)
def cached_forecast(zip_code):
    return weather_for_zip(zip_code)


def get_roster():
    source = roster_file if roster_file is not None else (ROOT / "sample_roster.csv" if use_sample_roster else None)
    if source is None:
        return None
    roster = load_roster(source)
    if roster.attrs.get("dropped_columns"):
        st.warning("We removed these columns because Heat Shield never needs them: "
                   + ", ".join(roster.attrs["dropped_columns"]))
    return roster


def get_weather():
    if weather_choice.startswith("Sample"):
        return load_station_csv(ROOT / "sample_weather.csv")
    if weather_choice.startswith("7-day"):
        return cached_forecast(zip_code)
    if station_file is None:
        return None
    return load_station_csv(station_file)


# ---------------- 3. Results ----------------
with results_tab:
    try:
        roster = get_roster()
        weather = get_weather()
    except (RosterError, WeatherError) as err:
        st.error(str(err))
        st.stop()

    if weather is None or weather.empty:
        st.warning("Choose or upload weather on the Upload tab.")
        st.stop()

    rule_id, rule_note = rule_for_state(state if state != "Other" else "")
    rule = rules[rule_id]
    st.subheader(f"Rule used: {rule['name']}")
    if rule_note:
        st.write(rule_note)
    st.caption(f"Source: {rule['source_url']} (checked {rule.get('verified_on')})")

    # Daily triggers
    st.subheader("Which rule applies each day")
    days = daily_triggers(weather, rule, clothing)
    st.dataframe(days, hide_index=True, width="stretch")
    alerts = days[days["niosh_heat_alert"]]
    if not alerts.empty:
        st.error("NIOSH heat alert on: " + ", ".join(str(d) for d in alerts["date"])
                 + ". Use extra caution and follow the slow-start calendar strictly.")

    # Work/rest
    st.subheader("Work/rest schedule")
    st.write(f"For **{workload}** work in **{clothing_label.lower()}**, in **{sun_label.lower()}**.")
    st.table(pd.DataFrame(band_table()))
    st.caption(f"Heat index rest breaks: Oregon OSHA OAR 437-002-0156(5)(e)(C), Table 2 ({OREGON_URL}).")

    hourly = add_work_rest(weather, workload, clothing, sun)
    hourly["date"] = pd.to_datetime(hourly["time"]).dt.date
    pick = st.selectbox("Hour by hour for", sorted(hourly["date"].unique()),
                        index=int(days["max_heat_index"].idxmax()))
    day_rows = hourly[(hourly["date"] == pick) & pd.to_datetime(hourly["time"]).dt.hour.between(6, 19)]
    st.dataframe(day_rows[["time", "temp_f", "rh", "heat_index", "advice", "source"]],
                 hide_index=True, width="stretch")
    st.caption("The schedule with more rest wins: the heat index table above, or the NIOSH "
               f"workload and clothing tables (NIOSH 2016-106, p. 76-77, {NIOSH_URL}). "
               "Assumptions: sun counts 7 am to 7 pm; humidity above 60% uses the 60% value.")

    # Acclimatization calendar
    st.subheader("Slow-start calendar (new and returning workers)")
    if roster is None:
        st.info("Upload a roster on the Upload tab to see the calendar.")
    else:
        first_day = min(days["date"])
        cal = calendar(roster, first_day, days=len(days), shift_hours=shift_hours)
        if cal.empty:
            st.success("No workers need a slow start in these dates.")
        else:
            st.write(f"Share of a {shift_hours}-hour shift each worker should spend in the heat.")
            st.dataframe(cal, hide_index=True, width="stretch")
        st.caption(f"Source: {ACCLIM_SOURCE}. New: 20, 40, 60, 80, 100%. Returning: 50, 60, 80, 100%. "
                   "Assumption: the worker works every day from their start or return date.")

st.divider()
st.caption(f"{NOT_LEGAL_ADVICE}  Rules file reviewed {rules_date}.  Built by Sujee Sathai for ChiEAC.")
