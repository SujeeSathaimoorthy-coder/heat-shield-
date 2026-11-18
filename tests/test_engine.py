"""Tests for the Week 3 engine: work/rest, acclimatization, triggers.

Expected values are copied from the primary sources:
- NIOSH 2016-106, p. 76-77 (work/rest tables) and Table 4-1, p. 34 (slow start)
- Oregon OAR 437-002-0156(5)(e)(C), Table 2 (heat index rest schedule)
"""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from acclimatization import calendar, exposure_percent
from loaders import load_roster
from triggers import daily_triggers, load_rules, niosh_heat_alert, rule_for_state, triggers
from weather import load_station_csv
from workrest import adjusted_temp, niosh_rest, oregon_rest, work_rest

ROOT = Path(__file__).resolve().parent.parent


# ---------- Oregon heat index schedule (Table 2) ----------
@pytest.mark.parametrize("hi, rest", [(89, 0), (90, 5), (94.9, 5), (95, 20), (100, 30), (105, 40), (115, 40)])
def test_oregon_table_2(hi, rest):
    assert oregon_rest(hi)[0] == rest


# ---------- NIOSH p. 76, normal clothing ----------
def test_adjusted_temp_full_sun_30_percent():
    assert adjusted_temp(90, 30, "full") == 103          # +13 for full sun


def test_adjusted_temp_humidity():
    assert adjusted_temp(90, 60, "none") == 99            # +9 at 60% RH
    assert adjusted_temp(90, 10, "none") == 82            # -8 at 10% RH
    assert adjusted_temp(90, 90, "none") == 99            # table stops at 60%


@pytest.mark.parametrize("t, workload, expected", [
    (94, "heavy", ("normal", 0)),
    (95, "heavy", ("schedule", 15)),      # 45/15
    (100, "moderate", ("schedule", 15)),  # 45/15
    (103, "heavy", ("schedule", 40)),     # 20/40
    (106, "light", ("schedule", 15)),     # 45/15
    (106, "heavy", ("caution", None)),
    (110, "light", ("schedule", 45)),     # 15/45
    (111, "light", ("caution", None)),
])
def test_niosh_normal_clothing(t, workload, expected):
    status, rest, _ = niosh_rest(t, 30, workload, "normal", "none")   # 30% RH, shade = no adjustment
    assert (status, rest) == expected


# ---------- NIOSH p. 77, chemical resistant suits ----------
@pytest.mark.parametrize("t, workload, sun, expected", [
    (80, "light", "full", ("schedule", 30)),      # 30/30
    (85, "moderate", "partly", ("schedule", 35)), # 25/35
    (90, "heavy", "none", ("schedule", 45)),      # 15/45
    (90, "light", "full", ("caution", None)),
    (95, "moderate", "full", ("stop", None)),
    (70, "heavy", "full", ("normal", 0)),         # below the table
    (82, "light", "full", ("schedule", 45)),      # between 80 and 85 -> use 85 (15/45)
])
def test_niosh_chemical_suit(t, workload, sun, expected):
    status, rest, _ = niosh_rest(t, 50, workload, "chemical_suit", sun)
    assert (status, rest) == expected


def test_more_rest_wins():
    # Heat index 100 -> Oregon says 30 min rest; light work in shade at 30% RH -> NIOSH normal
    r = work_rest(temp_f=95, rh=30, hi=100, workload="light", clothing="normal", sun="none")
    assert r["rest_min"] == 30 and "Oregon" in r["source"]


def test_bad_workload():
    with pytest.raises(ValueError):
        work_rest(90, 50, 95, workload="extreme")


# ---------- NIOSH slow start (Table 4-1) ----------
def test_new_worker_steps():
    assert [exposure_percent(d) for d in range(1, 7)] == [20, 40, 60, 80, 100, 100]


def test_returning_worker_steps():
    assert [exposure_percent(d, returning=True) for d in range(1, 6)] == [50, 60, 80, 100, 100]


def test_calendar_on_sample_roster():
    roster = load_roster(ROOT / "sample_roster.csv")
    cal = calendar(roster, date(2025, 6, 21), days=7, shift_hours=8)
    w001 = cal[cal["worker_id"] == "W001"].iloc[0]          # starts Sun Jun 22
    assert w001["Sat Jun 21"] == "not started"
    assert w001["Sun Jun 22"] == "20% (1.6 h)"
    w005 = cal[cal["worker_id"] == "W005"].iloc[0]          # back Tue Jun 24
    assert w005["Mon Jun 23"] == "away"
    assert w005["Tue Jun 24"] == "50% (4.0 h)"
    assert w005["type"] == "returning"


# ---------- Triggers ----------
def test_massachusetts_uses_federal_proposal():
    rule_id, note = rule_for_state("MA")
    assert rule_id == "federal_osha_proposed" and "no heat standard" in note


def test_california_uses_air_temperature():
    rules, _ = load_rules()
    lines = triggers(rules["california_outdoor"])
    assert lines[0][1:] == ("air_temp", 80) and lines[1][1:] == ("air_temp", 95)


def test_washington_vapor_barrier_trigger():
    rules, _ = load_rules()
    assert triggers(rules["washington_outdoor"], clothing="chemical_suit")[0][2] == 52


def test_niosh_heat_alert():
    assert niosh_heat_alert(96, [])
    assert niosh_heat_alert(92, [82])          # 10F hotter than before
    assert not niosh_heat_alert(92, [88])
    assert not niosh_heat_alert(89, [70])


def test_daily_triggers_on_sample_heat_wave():
    rules, _ = load_rules()
    weather = load_station_csv(ROOT / "sample_weather.csv")
    days = daily_triggers(weather, rules["federal_osha_proposed"])
    assert len(days) == 7
    june24 = days[days["date"] == date(2025, 6, 24)].iloc[0]
    assert june24["trigger_reached"].startswith("High heat")
    assert june24["niosh_heat_alert"]
    june27 = days[days["date"] == date(2025, 6, 27)].iloc[0]
    assert june27["trigger_reached"] == "None"
