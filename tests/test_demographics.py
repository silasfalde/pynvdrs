from pathlib import Path

import pandas as pd

from pynvdrs.demographics import (
    bin_age,
    get_processed_demographics,
    get_raw_demographics,
    load_demographics,
)


def _build_cases_csv(path: Path) -> Path:
    frame = pd.DataFrame(
        [
            {
                "PersonID": 1,
                "AgeYears_c": 20,
                "Sex": "Male",
                "Race_c": "White",
                "Ethnicity": "Hispanic",
                "SiteID": "Site A",
                "RaceEthnicity_c": "White, Hispanic",
                "MaritalStatus": "Single",
                "EducationLevel": "Bachelor's degree",
                "HousingInstability": "No",
                "OccupationText_DC": "student",
                "OccupationCurrentText": "student",
                "SexualOrientation": "Gay",
                "InjuryDate": "2024-01-02",
                "InjuryLocationType": "House, apartment",
                "BirthPlace": "Puerto Rico",
                "NarrativeCME": "",
                "NarrativeLE": "",
            },
            {
                "PersonID": 2,
                "AgeYears_c": 40,
                "Sex": "Female",
                "Race_c": "Black",
                "Ethnicity": "Non-Hispanic",
                "SiteID": "Site B",
                "RaceEthnicity_c": "Black, non-Hispanic",
                "MaritalStatus": "Married",
                "EducationLevel": "8th grade or less",
                "HousingInstability": "Unknown",
                "OccupationText_DC": "",
                "OccupationCurrentText": "prison inmate",
                "SexualOrientation": "Straight",
                "InjuryDate": "2024-07-06",
                "InjuryLocationType": "Natural area (e.g., field, river, beaches, woods)",
                "BirthPlace": "United States",
                "NarrativeCME": "",
                "NarrativeLE": "Moved from Puerto Rico last year.",
            },
            {
                "PersonID": 3,
                "AgeYears_c": 50,
                "Sex": "Male",
                "Race_c": "Asian",
                "Ethnicity": "Non-Hispanic",
                "SiteID": "Site C",
                "RaceEthnicity_c": "Asian, non-Hispanic",
                "MaritalStatus": "Single",
                "EducationLevel": "Some college credit, but no degree",
                "HousingInstability": "No",
                "OccupationText_DC": "employed",
                "OccupationCurrentText": "employed",
                "SexualOrientation": "Straight",
                "InjuryDate": "2024-03-01",
                "InjuryLocationType": "Unknown",
                "BirthPlace": "United States",
                "NarrativeCME": "",
                "NarrativeLE": "",
            },
        ]
    )
    frame.to_csv(path, index=False, encoding="latin1")
    return path


def test_bin_age():
    assert bin_age(17) == "<18"
    assert bin_age(27) == "18-34"
    assert bin_age(50) == "35-64"
    assert bin_age(70) == "65+"
    assert bin_age(None) == "unknown"


def test_load_demographics_and_helpers(tmp_path):
    csv_path = _build_cases_csv(tmp_path / "cases.csv")

    processed, raw = load_demographics(csv_path)

    assert list(processed.index) == [1, 2]
    assert processed.loc[1, "PR_origin"] == 1
    assert processed.loc[1, "EducationLevel"] == "some college or college degree"
    assert processed.loc[1, "SexualOrientation"] == "Not Heterosexual"
    assert processed.loc[1, "InjuryLocationType"] == "Home"
    assert processed.loc[1, "Season"] == "Winter"
    assert processed.loc[2, "Season"] == "Summer"
    assert processed.loc[2, "DayOfWeek"] == "Weekend"

    raw_row = get_raw_demographics(1, raw)
    processed_row = get_processed_demographics(1, processed)
    missing_row = get_processed_demographics(999, processed)

    assert raw_row["AgeYears_c"] == 20
    assert processed_row["PR_origin"] == 1
    assert missing_row.isna().all()

    selected = get_processed_demographics([1, 2], processed)
    assert list(selected.index) == [1, 2]