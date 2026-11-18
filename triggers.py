"""Trigger logic for Heat Shield: which rule applies on which day.

For each day of weather, finds the hottest hour and checks it against the
triggers of the chosen rule in heat_rules.yaml (for example 80 and 90 heat
index for the federal OSHA proposal). Also checks the NIOSH heat alert.
"""

from pathlib import Path

import pandas as pd
import yaml

RULES_FILE = Path(__file__).resolve().parent / "heat_rules.yaml"

# Which rule to use for each state. Massachusetts (and any state without a
# heat standard) uses the federal OSHA proposal as best practice.
STATE_RULE = {
    "CA": "california_outdoor",
    "WA": "washington_outdoor",
    "OR": "oregon",
    "MD": "maryland",
}
DEFAULT_RULE = "federal_osha_proposed"


def load_rules(path=RULES_FILE):
    """Read heat_rules.yaml. Returns {id: block}."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {j["id"]: j for j in data["jurisdictions"]}, data.get("last_reviewed")


def rule_for_state(state):
    """Pick the rule id for a 2-letter state code, plus a note for the user."""
    state = (state or "").upper()
    if state in STATE_RULE:
        return STATE_RULE[state], ""
    note = (f"{state or 'Your state'} has no heat standard for private employers, so Heat Shield "
            "uses the federal OSHA proposed rule (80/90 heat index) as best practice.")
    return DEFAULT_RULE, note


def triggers(rule, clothing="normal"):
    """The two trigger lines of a rule: [(name, measure, degrees F)].

    measure is "heat_index" or "air_temp" (California and Washington use air temperature).
    """
    lines = []
    if "initial_trigger_hi" in rule:
        lines.append(("Initial heat trigger", "heat_index", rule["initial_trigger_hi"]))
    elif "shade_trigger_f" in rule:
        lines.append(("Initial heat trigger", "air_temp", rule["shade_trigger_f"]))
    elif "action_trigger_f" in rule:
        value = rule["action_trigger_f"]
        if clothing == "chemical_suit" and "action_trigger_f_vapor_barrier_clothing" in rule:
            value = rule["action_trigger_f_vapor_barrier_clothing"]
        lines.append(("Initial heat trigger", "air_temp", value))

    if "high_heat_trigger_hi" in rule:
        lines.append(("High heat trigger", "heat_index", rule["high_heat_trigger_hi"]))
    elif "high_heat_trigger_f" in rule:
        lines.append(("High heat trigger", "air_temp", rule["high_heat_trigger_f"]))
    return lines


def what_applies(rule, level):
    """Plain words for what the rule requires at a trigger level."""
    items = []
    if level >= 1:
        if "water" in rule:
            items.append(f"Water: {rule['water']}")
        items.append("Shade or a cool-down area")
    if level >= 2:
        if "rest_high_heat" in rule:
            items.append(f"Rest: {rule['rest_high_heat']}")
        elif "rest" in rule:
            items.append(f"Rest: {rule['rest']}")
        items.append("Watch workers closely for signs of heat illness")
        items.append("New and returning workers follow the slow-start calendar")
    return items


def niosh_heat_alert(day_max_temp, previous_max_temps):
    """NIOSH 2016-106 s.1.7.4, p. 10: high above 95F, or above 90F and
    9F or more hotter than the days before."""
    if day_max_temp > 95:
        return True
    if day_max_temp > 90 and previous_max_temps:
        return day_max_temp - max(previous_max_temps) >= 9
    return False


def daily_triggers(weather, rule, clothing="normal"):
    """One row per day: hottest values, trigger reached, and what applies."""
    w = weather.copy()
    w["date"] = pd.to_datetime(w["time"]).dt.date
    lines = triggers(rule, clothing)

    rows = []
    previous = []
    for day, hours in w.groupby("date"):
        max_hi = hours["heat_index"].max()
        max_t = hours["temp_f"].max()
        level, reached, first_hour = 0, "None", None
        for i, (name, measure, value) in enumerate(lines, start=1):
            col = "heat_index" if measure == "heat_index" else "temp_f"
            hot = hours[hours[col] >= value]
            if not hot.empty:
                level, reached = i, f"{name} ({value}F {'heat index' if measure == 'heat_index' else 'air temp'})"
                first_hour = pd.to_datetime(hot["time"].iloc[0]).strftime("%H:%M")

        rows.append({
            "date": day,
            "max_temp_f": round(max_t, 1),
            "max_heat_index": round(max_hi, 1),
            "trigger_reached": reached,
            "from": first_hour or "",
            "niosh_heat_alert": niosh_heat_alert(max_t, previous[-3:]),
            "what_applies": "; ".join(what_applies(rule, level)) or "Normal work. Water always available.",
        })
        previous.append(max_t)
    return pd.DataFrame(rows)
