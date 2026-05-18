from itertools import product

import pandas as pd
import pytest

from pynvdrs.annotation import IAA, disagreements, find_disagreements, model_performance

pytest.importorskip("krippendorff")
pytest.importorskip("sklearn")


def _multiindex_annotations(frame):
    index = pd.MultiIndex.from_tuples(
        list(product([1, 2], ["A", "B"])), names=["PersonID", "Annotator"]
    )
    return pd.DataFrame(frame, index=index)


def test_disagreements_and_alias():
    annotations = _multiindex_annotations(
        {
            "CodeA": [1, 0, 1, 1],
            "CodeB": [0, 0, 1, 0],
        }
    )

    result = disagreements(annotations)
    alias_result = find_disagreements(annotations)

    assert result.equals(alias_result)
    assert set(result["Code"]) == {"CodeA", "CodeB"}
    assert len(result) == 2


def test_iaa_reports_perfect_agreement():
    annotations = _multiindex_annotations({"CodeA": [1, 1, 0, 0]})

    result = IAA(annotations)

    assert result.loc["CodeA", "Pairwise Agreement"] == 1.0
    assert result.loc["CodeA", "Cohen's Kappa"] == 1.0
    assert result.loc["CodeA", "Prevalence"] == 0.5


def test_model_performance_dataframe_path():
    human = pd.DataFrame({"CodeA": [1, 0], "CodeB": [0, 1]}, index=[1, 2])
    model = pd.DataFrame({"CodeA": [1, 0], "CodeB": [0, 1]}, index=[1, 2])

    result = model_performance(model, human)

    assert result.loc["CodeA", "F1"] == 1.0
    assert result.loc["CodeB", "Hamming loss"] == 0.0