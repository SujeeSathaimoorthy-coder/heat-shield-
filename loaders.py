"""Load a worker roster from CSV or Excel (XLSX) and check it.

If something is wrong, you get a RosterError with a plain-English
message that says which row and which column to fix.

PRIVACY: Heat Shield never needs names. If a file has columns like
"name" or "phone", they are thrown away as soon as the file is read.
"""

from pathlib import Path

import pandas as pd

# Columns every roster must have (worker_id is a code like W001, never a name)
REQUIRED_COLUMNS = ["worker_id", "site", "job", "start_date"]

# Columns we refuse to keep, because they identify a person
PRIVATE_COLUMNS = {"name", "first_name", "last_name", "full_name", "phone",
                   "phone_number", "email", "address", "ssn", "dob", "birth_date"}

TRUE_WORDS = {"true", "yes", "y", "1", "t"}
FALSE_WORDS = {"false", "no", "n", "0", "f", ""}


class RosterError(ValueError):
    """A problem in the roster file that the user needs to fix."""


def _read_file(source):
    """source can be a file path, or a file uploaded in the Streamlit app."""
    if hasattr(source, "read"):                  # uploaded file (kept in memory only)
        name = getattr(source, "name", "upload")
    else:
        source = Path(source)
        if not source.exists():
            raise RosterError(f"Could not find the file '{source}'. Check the name and folder.")
        name = source.name
    suffix = Path(name).suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(source, dtype=str, keep_default_na=False)
        if suffix in (".xlsx", ".xlsm"):
            return pd.read_excel(source, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        raise RosterError(f"The file '{name}' is empty.")
    raise RosterError(f"'{name}' is not a .csv or .xlsx file. Please save the roster as .csv or .xlsx.")


def _to_bool(value, row_num, column):
    text = str(value).strip().lower()
    if text in TRUE_WORDS:
        return True
    if text in FALSE_WORDS:
        return False
    raise RosterError(f"Row {row_num}: '{column}' should be yes/no or True/False, but it says '{value}'.")


def _parse_dates(df, column, problems):
    """Turn a text column into dates. Adds a message to problems for bad ones."""
    dates = pd.to_datetime(df[column], errors="coerce", format="mixed")
    for i in df.index[dates.isna() & (df[column] != "")]:
        problems.append(f"Row {i + 2}: {column} '{df.at[i, column]}' is not a date. Use YYYY-MM-DD, e.g. 2026-07-01.")
    return [d.date() if pd.notna(d) else None for d in dates]


def load_roster(source, today=None):
    """Read and check a roster. Returns a clean pandas table."""
    df = _read_file(source)
    file_name = getattr(source, "name", str(source))

    # Tidy column names: "Start Date" -> "start_date"
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # Privacy: drop name / phone / email columns straight away
    dropped = [c for c in df.columns if c in PRIVATE_COLUMNS]
    df = df.drop(columns=dropped)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise RosterError("The roster is missing these columns: " + ", ".join(missing) + ".")

    # Remove completely blank rows (common in Excel)
    df = df[df.apply(lambda r: "".join(map(str, r)).strip() != "", axis=1)].reset_index(drop=True)
    if df.empty:
        raise RosterError(f"'{Path(file_name).name}' has column names but no workers.")

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

    start_dates = _parse_dates(df, "start_date", problems)

    # return_date is optional: the day a worker comes back after a week or more away
    if "return_date" not in df.columns:
        df["return_date"] = ""
    return_dates = _parse_dates(df, "return_date", problems)

    if problems:
        raise RosterError("Please fix these problems in the roster:\n- " + "\n- ".join(problems))

    df["start_date"] = start_dates
    df["return_date"] = return_dates

    for i in df.index:
        r = df.at[i, "return_date"]
        if r is not None and r < df.at[i, "start_date"]:
            problems.append(f"Row {i + 2}: return_date {r} is before start_date {df.at[i, 'start_date']}.")

    # days_worked: use the column if it is there, otherwise count from start_date
    today = today or pd.Timestamp.today().date()
    if "days_worked" in df.columns:
        nums = pd.to_numeric(df["days_worked"], errors="coerce")
        for i in df.index[nums.isna() | (nums < 0)]:
            problems.append(f"Row {i + 2}: days_worked '{df.at[i, 'days_worked']}' should be a whole number, 0 or more.")
        df["days_worked"] = nums
    else:
        df["days_worked"] = [max((today - d).days, 0) for d in df["start_date"]]

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

    df.attrs["dropped_columns"] = dropped
    return df
