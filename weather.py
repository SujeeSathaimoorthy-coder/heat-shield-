"""Weather data for Heat Shield.

Three ways to get an hourly weather table (temperature, humidity, heat index):
1. weather_for_zip("02125") - free forecast from Open-Meteo (no API key)
2. load_station_csv(path)   - a CSV from a weather station (e.g. NOAA Boston Logan)
3. fetch_past_weather(...)  - real past weather from the Open-Meteo archive

Try it:  python weather.py 02125
Make the sample heat wave file:  python weather.py --sample
"""

import sys
from pathlib import Path

import pandas as pd
import requests

from heat_index import heat_index

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
ZIP_URL = "https://api.zippopotam.us/us/{zip}"


class WeatherError(RuntimeError):
    """Weather data could not be loaded."""


def _add_heat_index(df):
    df = df.dropna(subset=["temp_f", "rh"]).reset_index(drop=True)
    df["heat_index"] = [round(heat_index(t, h), 1) for t, h in zip(df["temp_f"], df["rh"])]
    return df


def zip_to_latlon(zip_code):
    """Turn a US ZIP code into (latitude, longitude, place name)."""
    zip_code = str(zip_code).strip()
    if not (zip_code.isdigit() and len(zip_code) == 5):
        raise WeatherError(f"'{zip_code}' is not a 5-digit US ZIP code.")
    resp = requests.get(ZIP_URL.format(zip=zip_code), timeout=20)
    if resp.status_code == 404:
        raise WeatherError(f"ZIP code {zip_code} was not found.")
    resp.raise_for_status()
    place = resp.json()["places"][0]
    return float(place["latitude"]), float(place["longitude"]), f"{place['place name']}, {place['state abbreviation']}"


def fetch_open_meteo(lat, lon, days=7, timezone="America/New_York"):
    """Hourly forecast from Open-Meteo for the next few days."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m",
        "temperature_unit": "fahrenheit",
        "forecast_days": days,
        "timezone": timezone,
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as err:
        raise WeatherError(f"Could not reach Open-Meteo: {err}") from err
    return parse_open_meteo(resp.json())


def fetch_past_weather(lat, lon, start_date, end_date, timezone="America/New_York"):
    """Hourly weather that already happened (Open-Meteo archive, free, no key).

    start_date / end_date look like "2025-06-21".
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m",
        "temperature_unit": "fahrenheit",
        "timezone": timezone,
    }
    try:
        resp = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as err:
        raise WeatherError(f"Could not reach the Open-Meteo archive: {err}") from err
    return parse_open_meteo(resp.json())


def parse_open_meteo(data):
    """Turn the Open-Meteo reply into a table."""
    try:
        hourly = data["hourly"]
        df = pd.DataFrame({
            "time": pd.to_datetime(hourly["time"]),
            "temp_f": hourly["temperature_2m"],
            "rh": hourly["relative_humidity_2m"],
        })
    except (KeyError, TypeError) as err:
        raise WeatherError(f"Open-Meteo reply was missing data: {err}") from err
    return _add_heat_index(df)


def weather_for_zip(zip_code, days=7):
    lat, lon, _ = zip_to_latlon(zip_code)
    return fetch_open_meteo(lat, lon, days=days)


def _clean_number(value):
    """NOAA values can look like '85s' (flagged) or '*' (missing). Keep just the number."""
    text = str(value).strip().rstrip("sV*").strip()
    try:
        return float(text)
    except ValueError:
        return None


def load_station_csv(source):
    """Read a station CSV: NOAA LCD format, or simple columns time, temp_f, rh.

    source can be a file path, or a file uploaded in the Streamlit app.
    """
    if not hasattr(source, "read"):              # a path, not an upload
        source = Path(source)
        if not source.exists():
            raise WeatherError(f"Could not find the station file '{source}'.")
    try:
        raw = pd.read_csv(source, dtype=str, low_memory=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        raise WeatherError("The station file could not be read. Please upload a .csv file.")

    if {"DATE", "HourlyDryBulbTemperature", "HourlyRelativeHumidity"} <= set(raw.columns):
        time_col, temp_col, rh_col = "DATE", "HourlyDryBulbTemperature", "HourlyRelativeHumidity"
    elif {"time", "temp_f", "rh"} <= set(raw.columns):
        time_col, temp_col, rh_col = "time", "temp_f", "rh"
    else:
        raise WeatherError(
            "Station CSV needs columns DATE, HourlyDryBulbTemperature, HourlyRelativeHumidity "
            "(NOAA) or time, temp_f, rh."
        )

    df = pd.DataFrame({
        "time": pd.to_datetime(raw[time_col], errors="coerce"),
        "temp_f": raw[temp_col].map(_clean_number),
        "rh": raw[rh_col].map(_clean_number),
    })
    df = df.dropna(subset=["time"])
    df = df[df["rh"].between(0, 100)]
    return _add_heat_index(df)


def save_sample_heat_wave(path="sample_weather.csv"):
    """Save the real Boston heat wave of June 21-27, 2025 (Dorchester, 02125)
    as a station-style CSV, so the app has a hot week to show in winter."""
    lat, lon, _ = zip_to_latlon("02125")
    df = fetch_past_weather(lat, lon, "2025-06-21", "2025-06-27")
    df[["time", "temp_f", "rh"]].to_csv(path, index=False)
    print(f"Saved {len(df)} hours to {path}. Hottest heat index: {df['heat_index'].max()}F")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sample":
        save_sample_heat_wave()
        sys.exit()
    zip_code = sys.argv[1] if len(sys.argv) > 1 else "02125"
    lat, lon, place = zip_to_latlon(zip_code)
    series = fetch_open_meteo(lat, lon)
    print(f"Weather for {zip_code} ({place}): {len(series)} hours loaded")
    print(series.head(12).to_string(index=False))
    peak = series.loc[series["heat_index"].idxmax()]
    print(f"\nHighest heat index this week: {peak['heat_index']}F at {peak['time']}")

