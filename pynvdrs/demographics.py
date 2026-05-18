"""Demographics helper functions and a loader that can process a NVDRS cases CSV.

This module intentionally avoids loading a dataset at import time; call `load_demographics`
with a path to the cases CSV to obtain processed and raw DataFrames.
"""

from typing import Optional, Tuple
import pandas as pd
import numpy as np
import re


PR_REGEX = re.compile(r"puerto ?ric[ao]", re.IGNORECASE)


def _bin_employment(row: pd.Series) -> str:
    employment_keywords = {
        "Student": ["student"],
        "Unemployed": ["unempl", "never", "none"],
        "Not in labor force": [
            "disab",
            "incar",
            "prison",
            "inmate",
            "correction",
            "retir",
        ],
        "Unknown": ["unk"],
    }

    for label in employment_keywords:
        if any(
            re.search(phrase, str(row[col]).lower())
            for phrase in employment_keywords[label]
            for col in row.index
            if pd.notna(row[col])
        ):
            return label

    return "Employed"


def _categorize_injury_location(location) -> str:
    if pd.isna(location) or location == "Unknown":
        return "Unknown"

    location_str = str(location)

    if location_str == "House, apartment":
        return "Home"
    elif location_str == "Natural area (e.g., field, river, beaches, woods)":
        return "Natural Area"
    elif (
        location_str
        == "Motor vehicle (excluding school bus, 15, and public transportation, 21)"
    ):
        return "Motor Vehicle (excluding public transportation)"
    else:
        return "Other"


def bin_age(age: Optional[int]) -> str:
    if age is None or (isinstance(age, float) and pd.isna(age)):
        return "unknown"
    try:
        a = int(age)
    except Exception:
        return "unknown"
    if a < 18:
        return "<18"
    if a < 35:
        return "18-34"
    if a < 65:
        return "35-64"
    return "65+"


def load_demographics(cases_csv: str | pd.PathLike) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load and return (processed_data, raw_data) derived from a NVDRS cases CSV.

    This mirrors the processing done in the original project but requires an explicit
    `cases_csv` path so the package is not tied to a single repository layout.
    """
    demographic_features = [
        "AgeYears_c",
        "Sex",
        "Race_c",
        "Ethnicity",
        "SiteID",
        "RaceEthnicity_c",
        "MaritalStatus",
        "EducationLevel",
        "HousingInstability",
        "OccupationText_DC",
        "OccupationCurrentText",
        "SexualOrientation",
        "InjuryDate",
        "InjuryLocationType",
    ]
    pr_origin_features = ["BirthPlace", "NarrativeCME", "NarrativeLE"]

    raw_data = pd.read_csv(
        cases_csv,
        usecols=["PersonID"] + demographic_features + pr_origin_features,
        index_col="PersonID",
        parse_dates=["InjuryDate"],
        encoding="latin1",
        low_memory=False,
    )

    _raw_demographic_data = raw_data[demographic_features].copy()

    processed_data = raw_data.copy()
    processed_data["AgeYears_c"] = pd.to_numeric(processed_data["AgeYears_c"], errors="coerce")
    processed_data = processed_data[(processed_data["AgeYears_c"] >= 15) & (processed_data["AgeYears_c"] <= 44)]
    processed_data["AgeYears_c"] = processed_data["AgeYears_c"].astype(int)

    pr_origins = processed_data["NarrativeLE"].str.contains(PR_REGEX, na=False) | (
        processed_data["NarrativeCME"].str.contains(PR_REGEX, na=False)
    )
    processed_data["PR_origin_flag"] = np.select(
        [processed_data["BirthPlace"] == "Puerto Rico", pr_origins],
        ["PR-born", "Other"],
        default="Not PR",
    )
    processed_data["PR_origin"] = (
        processed_data["PR_origin_flag"].map({"PR-born": 1, "Other": 1, "Not PR": 0}).astype(int)
    )
    processed_data = processed_data.drop(columns=["BirthPlace", "NarrativeCME", "NarrativeLE", "PR_origin_flag"])

    processed_data["EmploymentStatus"] = processed_data[["OccupationText_DC", "OccupationCurrentText"]].apply(_bin_employment, axis=1)
    processed_data = processed_data.drop(columns=["OccupationText_DC", "OccupationCurrentText"])

    education_map = {
        "High school graduate or GED completed": "high school diploma",
        "9th to 12th grade, no diploma": "No high school diploma",
        "Some college credit, but no degree": "some college or college degree",
        "8th grade or less": "No high school diploma",
        "Bachelor's degree": "some college or college degree",
        "Associate's degree": "some college or college degree",
        "Master's degree": "some college or college degree",
        "Doctorate or Professional degree": "some college or college degree",
    }
    processed_data["EducationLevel"] = processed_data["EducationLevel"].map(education_map).fillna("Unknown")

    sexual_orientation_map = {
        "Gay": "Not Heterosexual",
        "Lesbian": "Not Heterosexual",
        "Bisexual": "Not Heterosexual",
        "Unspecified sexual minority": "Not Heterosexual",
    }
    processed_data["SexualOrientation"] = processed_data["SexualOrientation"].replace(sexual_orientation_map).fillna("Unknown")

    processed_data["InjuryDate"] = pd.to_datetime(processed_data["InjuryDate"], errors="coerce")
    processed_data["Month"] = processed_data["InjuryDate"].dt.month
    processed_data["Season"] = (
        processed_data["Month"].map({
            1: "Winter",
            2: "Winter",
            3: "Spring",
            4: "Spring",
            5: "Spring",
            6: "Summer",
            7: "Summer",
            8: "Summer",
            9: "Fall",
            10: "Fall",
            11: "Fall",
            12: "Winter",
        }).fillna("Unknown")
    )
    processed_data["DayOfWeek"] = processed_data["InjuryDate"].dt.dayofweek.apply(
        lambda x: "Unknown" if pd.isna(x) else "Weekday" if x < 5 else "Weekend"
    )
    processed_data = processed_data.drop(columns=["InjuryDate", "Month"])

    processed_data["InjuryLocationType"] = processed_data["InjuryLocationType"].apply(_categorize_injury_location)

    return processed_data, _raw_demographic_data


def get_raw_demographics(person_id: int, raw_df: pd.DataFrame) -> Optional[pd.Series]:
    if raw_df is None:
        return None

    if person_id in raw_df.index:
        row = raw_df.loc[person_id]
        if isinstance(row, pd.DataFrame):
            return row.iloc[0]
        return row
    else:
        empty_series = pd.Series([np.nan] * len(raw_df.columns), index=raw_df.columns)
        empty_series.name = person_id
        return empty_series


def get_processed_demographics(person_id, processed_df: pd.DataFrame):
    if processed_df is None:
        return None

    if isinstance(person_id, (list, tuple, pd.Series)):
        person_ids = list(person_id)
        if len(person_ids) == 0:
            return processed_df.iloc[0:0].copy()
        return processed_df.reindex(person_ids)

    if person_id in processed_df.index:
        row = processed_df.loc[person_id]
        if isinstance(row, pd.DataFrame):
            return row.iloc[0]
        return row
    else:
        empty_series = pd.Series([np.nan] * len(processed_df.columns), index=processed_df.columns)
        empty_series.name = person_id
        return empty_series
