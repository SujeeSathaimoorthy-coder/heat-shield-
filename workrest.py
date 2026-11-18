"""Work/rest schedule for Heat Shield.

For every hour of weather, how many minutes should a worker work and rest?
Two published schedules are checked, and the one with MORE rest wins:

1. Heat index schedule - Oregon OSHA "simplified rest break schedule",
   OAR 437-002-0156(5)(e)(C), Table 2 (checked 2026-11-17, AO 1-2025, p. J-98).
2. Workload + clothing schedule - NIOSH 2016-106, Tables on p. 76-77,
   copied into Oregon's rule as Appendix A, Tables 3.1 and 3.2.

Assumptions Heat Shield adds (shown on screen and in the plan):
- Humidity is rounded to the nearest 10%. NIOSH's humidity list stops at 60%,
  so higher humidity uses the 60% value (the heat index schedule covers very humid days).
- Between the temperature columns of the chemical suit table, the next HOTTER column is used.
  Above 95 F in a chemical suit the answer is stop work.
- The sun setting from the survey counts from 7 am to 7 pm. At night NIOSH says
  no sun adjustment.
"""

import math

OREGON_URL = "https://osha.oregon.gov/OSHARules/div2/div2J.pdf"
NIOSH_URL = "https://www.cdc.gov/niosh/docs/2016-106/pdfs/2016-106.pdf"

OREGON_SOURCE = "Oregon OSHA OAR 437-002-0156(5)(e)(C), Table 2"
NIOSH_NORMAL_SOURCE = "NIOSH 2016-106, p. 76 (work/rest, normal clothing)"
NIOSH_SUIT_SOURCE = "NIOSH 2016-106, p. 77 (work/rest, chemical resistant suits)"

WORKLOADS = ["light", "moderate", "heavy"]
CLOTHING = ["normal", "chemical_suit"]
SUN = ["full", "partly", "none"]       # full sun / partly cloudy / shade or night

# What the NIOSH tables mean by "Caution"
CAUTION_TEXT = "High levels of heat stress; consider rescheduling activities."

# ---------- 1. Oregon heat index schedule ----------
# (lowest heat index, rest minutes per hour, words for the plan)
OREGON_BANDS = [
    (105, 40, "40 minutes rest every hour"),
    (100, 30, "30 minutes rest every hour"),
    (95, 20, "20 minutes rest every hour"),
    (90, 5, "10 minutes rest every two hours"),   # = 5 minutes per hour on average
]


def oregon_rest(hi):
    """Rest minutes per hour from the heat index alone (0 = normal breaks)."""
    for lowest, rest, words in OREGON_BANDS:
        if hi >= lowest:
            return rest, words
    return 0, "Normal breaks"


# ---------- 2. NIOSH workload + clothing tables ----------
SUN_ADJUST = {"full": 13, "partly": 7, "none": 0}
RH_ADJUST = {10: -8, 20: -4, 30: 0, 40: 3, 50: 6, 60: 9}

# NIOSH p. 76: adjusted temperature (F) -> "work/rest" for light, moderate, heavy.
# "N" = normal breaks, "C" = caution. Below 95 everything is normal,
# 111 and above everything is caution.
NIOSH_NORMAL = {
    95: ("N", "N", "45/15"), 96: ("N", "N", "45/15"), 97: ("N", "N", "40/20"),
    98: ("N", "N", "35/25"), 99: ("N", "N", "35/25"), 100: ("N", "45/15", "30/30"),
    101: ("N", "40/20", "30/30"), 102: ("N", "35/25", "25/35"), 103: ("N", "30/30", "20/40"),
    104: ("N", "30/30", "20/40"), 105: ("N", "25/35", "15/45"), 106: ("45/15", "20/40", "C"),
    107: ("40/20", "15/45", "C"), 108: ("35/25", "C", "C"), 109: ("30/30", "C", "C"),
    110: ("15/45", "C", "C"),
}

# NIOSH p. 77: chemical resistant suits, by AIR temperature (no adjustment).
# Columns are 75, 80, 85, 90, 95 F. "S" = stop work.
SUIT_COLUMNS = [75, 80, 85, 90, 95]
NIOSH_SUIT = {
    ("light", "full"): ["N", "30/30", "15/45", "C", "S"],
    ("light", "partly"): ["N", "N", "40/20", "15/45", "S"],
    ("light", "none"): ["N", "N", "N", "40/20", "15/45"],  # printed "14/45" in the table, a typo for 15/45
    ("moderate", "full"): ["N", "20/40", "10/50", "C", "S"],
    ("moderate", "partly"): ["N", "N", "25/35", "C", "S"],
    ("moderate", "none"): ["N", "N", "N", "25/35", "S"],
    ("heavy", "full"): ["35/25", "10/50", "C", "S", "S"],
    ("heavy", "partly"): ["N", "40/20", "15/45", "C", "S"],
    ("heavy", "none"): ["N", "N", "40/20", "15/45", "S"],
}


def adjusted_temp(temp_f, rh, sun):
    """NIOSH p. 76 note: add for sun, add or subtract for humidity."""
    rh_rounded = min(max(int(round(rh / 10.0)) * 10, 10), 60)
    return temp_f + SUN_ADJUST[sun] + RH_ADJUST[rh_rounded]


def _cell(code):
    """Turn a table cell into (status, rest minutes per hour)."""
    if code == "N":
        return "normal", 0
    if code == "C":
        return "caution", None
    if code == "S":
        return "stop", None
    work, rest = code.split("/")
    return "schedule", int(rest)


def niosh_rest(temp_f, rh, workload, clothing, sun):
    """Status and rest minutes per hour from the NIOSH tables."""
    if workload not in WORKLOADS:
        raise ValueError(f"workload must be one of {WORKLOADS}")
    if clothing not in CLOTHING:
        raise ValueError(f"clothing must be one of {CLOTHING}")
    if sun not in SUN:
        raise ValueError(f"sun must be one of {SUN}")

    if clothing == "chemical_suit":
        # The table starts at 75 F, and says stop work above 95 F
        if temp_f < 75:
            return "normal", 0, NIOSH_SUIT_SOURCE
        if temp_f > 95:
            return "stop", None, NIOSH_SUIT_SOURCE
        # Between columns, use the next hotter one (the safer side)
        col = math.ceil((temp_f - 75) / 5)
        status, rest = _cell(NIOSH_SUIT[(workload, sun)][col])
        return status, rest, NIOSH_SUIT_SOURCE

    t = int(round(adjusted_temp(temp_f, rh, sun)))
    if t < 95:
        return "normal", 0, NIOSH_NORMAL_SOURCE
    if t >= 111:
        return "caution", None, NIOSH_NORMAL_SOURCE
    code = NIOSH_NORMAL[t][WORKLOADS.index(workload)]
    status, rest = _cell(code)
    return status, rest, NIOSH_NORMAL_SOURCE


# ---------- Put them together ----------
def work_rest(temp_f, rh, hi, workload="moderate", clothing="normal", sun="full"):
    """Work/rest advice for one hour. Returns a dict for a table row."""
    o_rest, o_words = oregon_rest(hi)
    n_status, n_rest, n_source = niosh_rest(temp_f, rh, workload, clothing, sun)

    if n_status in ("caution", "stop"):
        return {
            "status": n_status,
            "work_min": None,
            "rest_min": None,
            "advice": "STOP WORK in the heat." if n_status == "stop" else CAUTION_TEXT,
            "source": n_source,
        }

    # The schedule with more rest wins
    if n_rest > o_rest:
        rest, source = n_rest, n_source
        advice = f"Work {60 - rest} min, rest {rest} min every hour"
    elif o_rest > 0:
        rest, source = o_rest, OREGON_SOURCE
        advice = o_words
    else:
        rest, source = 0, f"{OREGON_SOURCE}; {n_source}"
        advice = "Normal breaks"
    return {
        "status": "schedule" if rest else "normal",
        "work_min": 60 - rest,
        "rest_min": rest,
        "advice": advice,
        "source": source,
    }


def add_work_rest(weather, workload="moderate", clothing="normal", sun="full"):
    """Add work/rest columns to an hourly weather table (from weather.py)."""
    rows = []
    for time, t, h, hi in zip(weather["time"], weather["temp_f"], weather["rh"], weather["heat_index"]):
        hour = time.hour
        sun_now = sun if 7 <= hour < 19 else "none"     # no sun at night
        rows.append(work_rest(t, h, hi, workload, clothing, sun_now))
    out = weather.copy()
    for key in ("status", "work_min", "rest_min", "advice", "source"):
        out[key] = [r[key] for r in rows]
    return out


def band_table():
    """The heat index bands, for the plan and the results page."""
    rows = [{"heat_index": "below 80", "rest": "Normal breaks", "trigger": ""},
            {"heat_index": "80 - 89", "rest": "Normal breaks + rest whenever a worker asks",
             "trigger": "Initial heat trigger (80)"}]
    for lowest, _, words in reversed(OREGON_BANDS):
        label = "105 and above" if lowest == 105 else f"{lowest} - {lowest + 4}"
        rows.append({"heat_index": label, "rest": words,
                     "trigger": "High heat trigger (90)" if lowest == 90 else ""})
    return rows
