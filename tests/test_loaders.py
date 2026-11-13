from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from loaders import RosterError, load_roster

ROOT = Path(__file__).resolve().parent.parent
HEADER = "worker_id,name,site,job,start_date\n"


def write(tmp_path, text, name="roster.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_sample_roster_loads():
    df = load_roster(ROOT / "sample_roster.csv")
    assert len(df) == 25


def test_xlsx_loads(tmp_path):
    xlsx = tmp_path / "roster.xlsx"
    pd.read_csv(ROOT / "sample_roster.csv").to_excel(xlsx, index=False)
    assert len(load_roster(xlsx)) == 25


def test_days_worked_counted_from_start_date(tmp_path):
    p = write(tmp_path, HEADER + "W1,Ana,Site A,Roofer,2026-07-10\n")
    df = load_roster(p, today=date(2026, 7, 15))
    assert df.loc[0, "days_worked"] == 5
    assert not df.loc[0, "acclimatized"]


def test_missing_file():
    with pytest.raises(RosterError, match="Could not find"):
        load_roster("nope.csv")


def test_wrong_file_type(tmp_path):
    p = write(tmp_path, "hello", name="roster.txt")
    with pytest.raises(RosterError, match=".csv or .xlsx"):
        load_roster(p)


def test_missing_columns(tmp_path):
    p = write(tmp_path, "worker_id,name\nW1,Ana\n")
    with pytest.raises(RosterError, match="missing these columns"):
        load_roster(p)


def test_blank_name(tmp_path):
    p = write(tmp_path, HEADER + "W1,Ana,A,Roofer,2026-07-10\nW2,,A,Roofer,2026-07-10\n")
    with pytest.raises(RosterError, match="Row 3: 'name' is blank"):
        load_roster(p)


def test_bad_date(tmp_path):
    p = write(tmp_path, HEADER + "W1,Ana,A,Roofer,last tuesday\n")
    with pytest.raises(RosterError, match="is not a date"):
        load_roster(p)


def test_duplicate_ids(tmp_path):
    p = write(tmp_path, HEADER + "W1,Ana,A,Roofer,2026-07-10\nW1,Bo,A,Roofer,2026-07-10\n")
    with pytest.raises(RosterError, match="used more than once"):
        load_roster(p)


def test_bad_yes_no(tmp_path):
    p = write(tmp_path, "worker_id,name,site,job,start_date,acclimatized\nW1,Ana,A,Roofer,2026-07-10,maybe\n")
    with pytest.raises(RosterError, match="should be yes/no"):
        load_roster(p)


def test_header_only(tmp_path):
    p = write(tmp_path, HEADER)
    with pytest.raises(RosterError, match="no workers"):
        load_roster(p)
