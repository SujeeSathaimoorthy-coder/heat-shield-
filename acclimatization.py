"""Acclimatization calendar for Heat Shield.

New and returning workers need a slow start in the heat. This file makes a
day-by-day calendar: what share of a normal shift each worker should spend
in the heat.

Source: NIOSH 2016-106, Table 4-1, p. 34 (see heat_rules.yaml, id: niosh)
  New worker:        20%, 40%, 60%, 80%, then 100%
  Returning worker:  50%, 60%, 80%, then 100%  (back after a week or more away)

Heat Shield assumption (shown on screen): the roster has no daily shifts yet,
so we assume the worker works every day from their start or return date.
If they miss days, they should start lower again.
"""

from datetime import timedelta

import pandas as pd

SOURCE = "NIOSH 2016-106, Table 4-1, p. 34"
NEW_WORKER = [20, 40, 60, 80, 100]
RETURNING_WORKER = [50, 60, 80, 100]


def exposure_percent(day_number, returning=False):
    """Day 1 = first day on the job (or first day back). Returns 20-100."""
    if day_number < 1:
        raise ValueError("day_number starts at 1")
    steps = RETURNING_WORKER if returning else NEW_WORKER
    return steps[min(day_number, len(steps)) - 1]


def worker_status(row, day):
    """For one worker on one date: (percent or None, "new" / "returning" / words)."""
    start = row["start_date"]
    back = row.get("return_date")
    has_return = back is not None and pd.notna(back)

    if day < start:
        return None, "not started"
    if has_return and day < back:
        return None, "away"
    if has_return:
        return exposure_percent((day - back).days + 1, returning=True), "returning"
    return exposure_percent((day - start).days + 1, returning=False), "new"


def calendar(roster, first_day, days=7, shift_hours=8):
    """Table: one row per worker who needs a slow start, one column per date.

    Each cell looks like "40% (3.2 h)". Workers at 100% every day are left out.
    """
    dates = [first_day + timedelta(days=i) for i in range(days)]
    rows = []
    for _, worker in roster.iterrows():
        cells = {}
        needs_slow_start = False
        worker_type = "new"
        for d in dates:
            pct, kind = worker_status(worker, d)
            if kind == "returning":
                worker_type = "returning"
            if pct is None:
                cells[d] = kind
            elif pct == 100:
                cells[d] = "100%"
            else:
                needs_slow_start = True
                cells[d] = f"{pct}% ({shift_hours * pct / 100:.1f} h)"
        if needs_slow_start:
            rows.append({"worker_id": worker["worker_id"], "site": worker["site"],
                         "job": worker["job"], "type": worker_type,
                         **{d.strftime("%a %b %d"): cells[d] for d in dates}})
    return pd.DataFrame(rows)
