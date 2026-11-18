import pytest

from weather import WeatherError, load_station_csv, parse_open_meteo, weather_for_zip

FAKE_REPLY = {
    "hourly": {
        "time": ["2026-07-15T13:00", "2026-07-15T14:00"],
        "temperature_2m": [90.0, 96.0],
        "relative_humidity_2m": [60, 50],
    }
}


def test_parse_open_meteo():
    df = parse_open_meteo(FAKE_REPLY)
    assert list(df.columns) == ["time", "temp_f", "rh", "heat_index"]
    assert len(df) == 2
    assert df.loc[0, "heat_index"] > df.loc[0, "temp_f"]


def test_parse_open_meteo_bad_reply():
    with pytest.raises(WeatherError):
        parse_open_meteo({"error": True})


def test_noaa_station_csv(tmp_path):
    p = tmp_path / "lcd.csv"
    p.write_text(
        "STATION,DATE,HourlyDryBulbTemperature,HourlyRelativeHumidity\n"
        "72509014739,2026-07-15T13:54:00,90,60\n"
        "72509014739,2026-07-15T14:54:00,92s,55\n"
        "72509014739,2026-07-15T15:54:00,*,\n",
        encoding="utf-8",
    )
    df = load_station_csv(p)
    assert len(df) == 2
    assert df.loc[1, "temp_f"] == 92


def test_simple_station_csv(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("time,temp_f,rh\n2026-07-15 13:00,85,70\n", encoding="utf-8")
    assert len(load_station_csv(p)) == 1


def test_station_csv_wrong_columns(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(WeatherError, match="needs columns"):
        load_station_csv(p)


def test_bad_zip():
    with pytest.raises(WeatherError, match="5-digit"):
        weather_for_zip("abc")


def test_live_dorchester_zip():
    # Needs internet: loads 2 days of real forecast for 02125
    df = weather_for_zip("02125", days=2)
    assert len(df) == 48


def test_station_csv_uploaded_in_memory():
    import io
    upload = io.BytesIO(b"time,temp_f,rh\n2025-06-24 14:00,95,50\n")
    upload.name = "station.csv"          # Streamlit uploads have a .name
    df = load_station_csv(upload)
    assert len(df) == 1 and df.loc[0, "heat_index"] > 95
