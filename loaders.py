"""Load a worker roster from CSV or Excel (XLSX) and check it.

If something is wrong, you get a RosterError with a plain-English
message that says which row and which column to fix.
"""

from pathlib import Path

import pandas as pd

# Columns every roster must have
REQUIRED_COLUMNS = ["worker_id", "name", "site", "job", "start_date"]

TRUE_WORDS = {"true", "yes", "y", "1", "t"}
FALSE_WORDS = {"false", "no", "n", "0", "f", ""}


class RosterError(ValueError):
    """A problem in the roster file that the user needs to fix."""


def _read_file(path):
    if not path.exists():
        raise RosterError(f"Could not find the file '{path}'. Check the name and folder.")
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(path, dtype=str, keep_default_na=False)
        if suffix in (".xlsx", ".xlsm"):
            return pd.read_excel(path, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        raise RosterError(f"The file '{path.name}' is empty.")
    raise RosterError(f"'{path.name}' is not a .csv or .xlsx file. Please save the roster as .csv or .xlsx.")


def _to_bool(value, row_num, column):
    text = str(value).strip().lower()
    if text in TRUE_WORDS:
        return True
    if text in FALSE_WORDS:
        return False
    raise RosterError(f"Row {row_num}: '{column}' should be yes/no or True/False, but it says '{value}'.")


def load_roster(path, today=None):
    """Read and check a roster. Returns a clean pandas table."""
    path = Path(path)
    df = _read_file(path)

    # Tidy column names: "Start Date" -> "start_date"
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise RosterError("The roster is missing these columns: " + ", ".join(missing) + ".")

    # Remove completely blank rows (common in Excel)
    df = df[df.apply(lambda r: "".join(map(str, r)).strip() != "", axis=1)].reset_index(drop=True)
    if df.empty:
        raise RosterError(f"'{path.name}' has column names but no workers.")

    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    problems = []
    # Row numbers match the spreadsheet (row 1 is the header)
    for i, row in df.iterrows():
        for col in REQUIRED_COLUMNS:
            if row[col] == "":
                problems.append(f"Row {i + 2}: '{col}' is blank.")

    dupes = df.loc[df["worker_id"].duplicated() & (df["worker_id"] != ""), "worker_id"]
    for wid in dupes.unique():
        problems.append(f"worker_id '{wid}' is used more than once.")

    dates = pd.to_datetime(df["start_date"], errors="coerce", format="mixed")
    for i in df.index[dates.isna() & (df["start_date"] != "")]:
        problems.append(f"Row {i + 2}: start_date '{df.at[i, 'start_date']}' is not a date. Use YYYY-MM-DD, e.g. 2026-07-01.")

    if problems:
        raise RosterError("Please fix these problems in the roster:\n- " + "\n- ".join(problems))

    df["start_date"] = dates.dt.date

    # days_worked: use the column if it is there, otherwise count from start_date
    today = today or pd.Timestamp.today().date()
    if "days_worked" in df.columns:
        nums = pd.to_numeric(df["days_worked"], errors="coerce")
        for i in df.index[nums.isna() | (nums < 0)]:
            problems.append(f"Row {i + 2}: days_worked '{df.at[i, 'days_worked']}' should be a whole number, 0 or more.")
        df["days_worked"] = nums
    else:
        df["days_worked"] = [(today - d).days for d in df["start_date"]]

    if problems:
        raise RosterError("Please fix these problems in the roster:\n- " + "\n- ".join(problems))
    df["days_worked"] = df["days_worked"].astype(int)

    for col in ("is_new", "acclimatized"):
        if col in df.columns:
            df[col] = [_to_bool(v, i + 2, col) for i, v in df[col].items()]

    # NIOSH: about 14 days to get used to heat
    if "acclimatized" not in df.columns:
        df["acclimatized"] = df["days_worked"] >= 14
    if "is_new" not in df.columns:
        df["is_new"] = df["days_worked"] < 14

    return df
