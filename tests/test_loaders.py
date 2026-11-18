import io
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from loaders import RosterError, load_roster

ROOT = Path(__file__).resolve().parent.parent
HEADER = "worker_id,site,job,start_date\n"


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
    p = write(tmp_path, HEADER + "W1,Site A,Roofer,2026-07-10\n")
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
    p = write(tmp_path, "worker_id,site\nW1,A\n")
    with pytest.raises(RosterError, match="missing these columns"):
        load_roster(p)


def test_blank_site(tmp_path):
    p = write(tmp_path, HEADER + "W1,A,Roofer,2026-07-10\nW2,,Roofer,2026-07-10\n")
    with pytest.raises(RosterError, match="Row 3: 'site' is blank"):
        load_roster(p)


def test_bad_date(tmp_path):
    p = write(tmp_path, HEADER + "W1,A,Roofer,last tuesday\n")
    with pytest.raises(RosterError, match="is not a date"):
        load_roster(p)


def test_duplicate_ids(tmp_path):
    p = write(tmp_path, HEADER + "W1,A,Roofer,2026-07-10\nW1,A,Roofer,2026-07-10\n")
    with pytest.raises(RosterError, match="used more than once"):
        load_roster(p)


def test_bad_yes_no(tmp_path):
    p = write(tmp_path, "worker_id,site,job,start_date,acclimatized\nW1,A,Roofer,2026-07-10,maybe\n")
    with pytest.raises(RosterError, match="should be yes/no"):
        load_roster(p)


def test_header_only(tmp_path):
    p = write(tmp_path, HEADER)
    with pytest.raises(RosterError, match="no workers"):
        load_roster(p)


# ---- Week 3: privacy, return dates, uploads ----

def test_name_and_phone_columns_are_removed(tmp_path):
    p = write(tmp_path, "worker_id,name,phone,site,job,start_date\n"
                        "W1,Ana,617-555-0000,A,Roofer,2026-07-10\n")
    df = load_roster(p)
    assert "name" not in df.columns and "phone" not in df.columns
    assert df.attrs["dropped_columns"] == ["name", "phone"]


def test_sample_roster_has_no_names():
    df = load_roster(ROOT / "sample_roster.csv")
    assert df.attrs["dropped_columns"] == []


def test_return_date_is_read(tmp_path):
    p = write(tmp_path, "worker_id,site,job,start_date,return_date\n"
                        "W1,A,Roofer,2026-05-01,2026-07-10\n"
                        "W2,A,Roofer,2026-05-01,\n")
    df = load_roster(p)
    assert df.loc[0, "return_date"] == date(2026, 7, 10)
    assert df.loc[1, "return_date"] is None


def test_return_before_start_is_an_error(tmp_path):
    p = write(tmp_path, "worker_id,site,job,start_date,return_date\n"
                        "W1,A,Roofer,2026-07-10,2026-05-01\n")
    with pytest.raises(RosterError, match="before start_date"):
        load_roster(p)


def test_uploaded_file_in_memory():
    upload = io.BytesIO(b"worker_id,site,job,start_date\nW1,A,Roofer,2026-07-10\n")
    upload.name = "roster.csv"          # Streamlit uploads have a .name
    assert len(load_roster(upload)) == 1
