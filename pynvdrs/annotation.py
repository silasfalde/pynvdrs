"""Annotation utilities for disagreement review, IAA, model scoring, and resolution."""

from __future__ import annotations

import warnings
from itertools import combinations
from typing import List

import pandas as pd

__all__ = [
    "IAA",
    "disagreements",
    "find_disagreements",
    "model_performance",
    "resolve_disagreements",
    "sample",
]


def _require_krippendorff():
    try:
        import krippendorff
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("Install pynvdrs[iaa] to use IAA utilities.") from exc

    return krippendorff


def _require_sklearn_metrics():
    try:
        from sklearn.metrics import cohen_kappa_score, hamming_loss, precision_recall_fscore_support
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("Install pynvdrs[iaa] to use annotation metrics.") from exc

    return cohen_kappa_score, hamming_loss, precision_recall_fscore_support


def _set_future_downcasting_option() -> None:
    return None


def disagreements(annotations: pd.DataFrame) -> pd.DataFrame:
    """Return row-level annotation disagreements for a MultiIndex DataFrame."""

    if not isinstance(annotations.index, pd.MultiIndex) or annotations.index.nlevels < 2:
        raise ValueError("annotations must use a MultiIndex with PersonID and Annotator levels.")

    id_col = str(annotations.index.names[0])
    annotator_col = str(annotations.index.names[1])

    rows = []
    for code in annotations.columns:
        for person_id, group in annotations.groupby(level=0):
            pairs = [
                (annotator, annotation)
                for annotator, annotation in zip(
                    group.index.get_level_values(1), group[code]
                )
            ]

            seen_pairs = set()
            for (annot1, ann1), (annot2, ann2) in combinations(pairs, 2):
                if pd.isna(ann1) or pd.isna(ann2):
                    continue

                if ann1 != ann2:
                    pair_key = tuple(sorted([str(annot1), str(annot2)]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    a1, v1, a2, v2 = (
                        pair_key[0],
                        ann1 if str(annot1) == pair_key[0] else ann2,
                        pair_key[1],
                        ann2 if str(annot2) == pair_key[1] else ann1,
                    )
                    rows.append([person_id, code, a1, v1, a2, v2])

    result = pd.DataFrame(
        rows,
        columns=[
            id_col,
            "Code",
            f"{annotator_col} 1",
            "Annotation 1",
            f"{annotator_col} 2",
            "Annotation 2",
        ],
    )
    result = result.sort_values([id_col, "Code"]).reset_index(drop=True)
    return result


def find_disagreements(annotations: pd.DataFrame) -> pd.DataFrame:
    """Backward-compatible alias for :func:`disagreements`."""

    return disagreements(annotations)


def IAA(annotations: pd.DataFrame, metrics: List[str] | None = None) -> pd.DataFrame:
    """Compute inter-annotator agreement metrics for each code."""

    _set_future_downcasting_option()
    codes = list(annotations.columns)
    iaa = pd.DataFrame({"Code": codes}).set_index("Code")

    if metrics is None:
        metrics = ["prevalence", "krippendorff", "cohen", "pairwise"]

    metric_names = {
        "krippendorff": "Krippendorff's Alpha",
        "cohen": "Cohen's Kappa",
        "prevalence": "Prevalence",
        "pairwise": "Pairwise Agreement",
    }

    for metric in metrics:
        if metric not in metric_names:
            raise ValueError(f"Unsupported metric: {metric}")
        iaa[metric_names[metric]] = None

    if "krippendorff" in metrics:
        krippendorff = _require_krippendorff()

        alphas = {}

        for col in codes:
            data = annotations[col].unstack(level=1).T.values
            try:
                alpha = krippendorff.alpha(
                    reliability_data=data, level_of_measurement="nominal"
                )
            except Exception:
                alpha = None

            if alpha is None:
                pivot = annotations[col].unstack(level=1).T
                arr = pivot.values
                if arr.dtype.kind in ("O", "U", "S"):
                    cats = pd.Categorical(annotations[col].dropna())
                    mapping = {cat: code for code, cat in enumerate(cats.categories)}
                    pivot_mapped = pivot.replace(mapping)
                    data = pivot_mapped.astype(float).values
                else:
                    data = arr.astype(float, copy=False)

                try:
                    alpha = krippendorff.alpha(
                        reliability_data=data, level_of_measurement="nominal"
                    )
                except Exception:
                    alpha = None

            alphas[col] = alpha

        iaa[metric_names["krippendorff"]] = iaa.index.map(alphas)

    if "cohen" in metrics:
        cohen_score, _, _ = _require_sklearn_metrics()

        cohens = {}

        for col in codes:
            kappa_scores = []
            all_labels = annotations[col].dropna().unique()
            annotators = annotations.index.get_level_values(1).unique()

            if len(annotators) >= 2:
                for annot1, annot2 in combinations(annotators, 2):
                    data1 = annotations.xs(annot1, level=1)[col]
                    data2 = annotations.xs(annot2, level=1)[col]
                    common_ids = data1.index.intersection(data2.index)
                    if len(common_ids) > 0:
                        y1 = data1.loc[common_ids].values
                        y2 = data2.loc[common_ids].values
                        valid_mask = ~(pd.isna(y1) | pd.isna(y2))
                        y1_valid = y1[valid_mask]
                        y2_valid = y2[valid_mask]

                        if len(y1_valid) > 0:
                            try:
                                with warnings.catch_warnings():
                                    warnings.filterwarnings(
                                        "ignore",
                                        message="invalid value encountered in scalar divide",
                                        category=RuntimeWarning,
                                    )
                                    kappa = cohen_score(
                                        y1_valid, y2_valid, labels=all_labels  # type: ignore
                                    )
                                kappa_scores.append(kappa)
                            except Exception:
                                pass

                cohens[col] = (
                    sum(kappa_scores) / len(kappa_scores) if kappa_scores else None
                )
            else:
                cohens[col] = None

        iaa[metric_names["cohen"]] = iaa.index.map(cohens)

    if "prevalence" in metrics:
        prevalences = {}

        for col in codes:
            col_data = annotations[col].dropna()
            if col_data.dtype == "object" or col_data.dtype.name == "category":
                prevalences[col] = None
            else:
                positive_count = (col_data == 1).sum()
                prevalences[col] = positive_count / len(col_data)

        iaa[metric_names["prevalence"]] = iaa.index.map(prevalences)

    if "pairwise" in metrics:
        pairwises = {}

        for col in codes:
            agreements = []
            annotators = annotations.index.get_level_values(1).unique()

            if len(annotators) >= 2:
                for annot1, annot2 in combinations(annotators, 2):
                    data1 = annotations.xs(annot1, level=1)[col]
                    data2 = annotations.xs(annot2, level=1)[col]
                    common_ids = data1.index.intersection(data2.index)
                    if len(common_ids) > 0:
                        y1 = data1.loc[common_ids].values
                        y2 = data2.loc[common_ids].values
                        valid_mask = ~(pd.isna(y1) | pd.isna(y2))
                        y1_valid = y1[valid_mask]
                        y2_valid = y2[valid_mask]

                        if len(y1_valid) > 0:
                            agreement = (y1_valid == y2_valid).sum() / len(y1_valid)  # type: ignore
                            agreements.append(agreement)

                pairwises[col] = (
                    sum(agreements) / len(agreements) if agreements else None
                )
            else:
                pairwises[col] = None

        iaa[metric_names["pairwise"]] = iaa.index.map(pairwises)

    return iaa


def model_performance(
    model_annotations: pd.Series | pd.DataFrame,
    human_annotations: pd.Series | pd.DataFrame,
    one_hot_encode: bool = False,
) -> pd.DataFrame:
    """Compare model annotations against human annotations."""

    _, hamming_loss, precision_recall_fscore_support = _require_sklearn_metrics()

    def _binary_prevalence(series: pd.Series) -> float:
        values = series.dropna()
        if values.empty:
            return float("nan")

        unique_values = set(values.unique())
        if unique_values.issubset({0, 1}):
            return float((values == 1).sum()) / len(values)

        return float("nan")

    if isinstance(human_annotations, pd.DataFrame) and isinstance(
        model_annotations, pd.DataFrame
    ):
        human = human_annotations.copy()
        model = model_annotations.copy()

        if one_hot_encode:

            def _prepare_one_hot(df: pd.DataFrame) -> pd.DataFrame:
                prepared = df.copy()

                all_missing_cols = prepared.columns[prepared.isna().all()]
                if len(all_missing_cols) > 0:
                    prepared = prepared.drop(columns=all_missing_cols)

                prepared = pd.get_dummies(prepared, drop_first=False)

                if prepared.columns.has_duplicates:
                    prepared = prepared.T.groupby(level=0).max().T

                return prepared

            human = _prepare_one_hot(human)
            model = _prepare_one_hot(model)

            human, model = human.align(model, join="outer", axis=1, fill_value=0)

        human, model = human.align(
            model, join="inner", axis=0
        )
        if human.empty:
            raise ValueError(
                "No overlapping rows between model and human annotations after index alignment."
            )

        common_columns = human.columns.intersection(model.columns)
        if common_columns.empty:
            raise ValueError(
                "No overlapping columns between model and human annotations."
            )

        human = human[common_columns]
        model = model[common_columns]

        metrics = []
        for col in common_columns:
            paired = pd.concat(
                [human[col], model[col]], axis=1, keys=["human", "model"]
            ).dropna()

            if paired.empty:
                metrics.append(
                    [
                        col,
                        float("nan"),
                        float("nan"),
                        float("nan"),
                        float("nan"),
                        float("nan"),
                        float("nan"),
                    ]
                )
                continue

            p, r, f, _ = precision_recall_fscore_support(
                paired["human"],
                paired["model"],
                average="weighted",
                zero_division=0,
            )
            h = hamming_loss(paired["human"], paired["model"])
            human_prev = _binary_prevalence(paired["human"])
            model_prev = _binary_prevalence(paired["model"])
            metrics.append([col, p, r, f, h, human_prev, model_prev])

    elif isinstance(human_annotations, pd.Series) and isinstance(
        model_annotations, pd.Series
    ):
        paired = pd.concat(
            [
                human_annotations.rename("human"),
                model_annotations.rename("model"),
            ],
            axis=1,
        ).dropna()

        if paired.empty:
            raise ValueError(
                "No overlapping non-missing samples between model and human annotations."
            )

        precision, recall, f1, _ = precision_recall_fscore_support(
            paired["human"], paired["model"], average="weighted", zero_division=0
        )
        h = hamming_loss(paired["human"], paired["model"])
        human_prev = _binary_prevalence(paired["human"])
        model_prev = _binary_prevalence(paired["model"])
        metrics = [["Overall", precision, recall, f1, h, human_prev, model_prev]]

    else:
        raise TypeError(
            "model_annotations and human_annotations must both be DataFrames or both be Series."
        )

    return pd.DataFrame(
        metrics,
        columns=[
            "Code",
            "Precision",
            "Recall",
            "F1",
            "Hamming loss",
            "Human Prevalence",
            "Model Prevalence",
        ],
    ).set_index("Code")


def sample(
    annotators: List[str],
    cases_per_annotator: int,
    overlap_proportion: float,
    cases: pd.DataFrame,
) -> pd.DataFrame:
    """Sample overlapping annotator assignments from a case pool."""

    import numpy as np

    overlap_n = int(cases_per_annotator * overlap_proportion)

    def stratified_sample(df, total_n, random_state=None):
        us_n = total_n // 2
        pr_n = total_n - us_n
        us_prorigin_n = us_n // 2
        us_nonprorigin_n = us_n - us_prorigin_n

        us_prorigin_cases = df[(df["SiteID"] != "Puerto Rico") & (df["PR_origin"] == 1)]
        us_nonprorigin_cases = df[(df["SiteID"] != "Puerto Rico") & (df["PR_origin"] == 0)]
        pr_cases = df[df["SiteID"] == "Puerto Rico"]

        assert len(us_prorigin_cases) >= us_prorigin_n, "Not enough US PR-origin cases"
        assert (
            len(us_nonprorigin_cases) >= us_nonprorigin_n
        ), "Not enough US non-PR-origin cases"
        assert len(pr_cases) >= pr_n, "Not enough PR cases"

        sample_us_prorigin = us_prorigin_cases.sample(n=us_prorigin_n, random_state=random_state)
        sample_us_nonprorigin = us_nonprorigin_cases.sample(n=us_nonprorigin_n, random_state=random_state)
        sample_pr = pr_cases.sample(n=pr_n, random_state=random_state)

        sample = pd.concat([sample_us_prorigin, sample_us_nonprorigin, sample_pr])
        return sample

    possible_pairs = list(combinations(annotators, 2))
    assignments = {a: set() for a in annotators}
    case_pool = cases.copy()
    all_available_indices = set(case_pool.index)
    pairwise_assignment = {pair: set() for pair in possible_pairs}

    for pair in possible_pairs:
        available_for_pair = case_pool.loc[
            list(all_available_indices - set.union(*pairwise_assignment.values()))
        ]
        strat_sample = stratified_sample(
            available_for_pair, overlap_n, random_state=np.random.randint(42)
        )
        selected_indices = set(strat_sample.index)
        pairwise_assignment[pair].update(selected_indices)
        assignments[pair[0]].update(selected_indices)
        assignments[pair[1]].update(selected_indices)

    for a in annotators:
        already_assigned = assignments[a]
        remaining_needed = cases_per_annotator - len(already_assigned)
        available_df = case_pool.loc[list(all_available_indices - already_assigned)]
        unique_stratified = stratified_sample(available_df, remaining_needed, random_state=42)
        assignments[a].update(unique_stratified.index)

    annotator_samples = []
    for a in annotators:
        sample_df = case_pool.loc[list(assignments[a])].copy()
        sample_df["Annotator"] = a
        annotator_samples.append(sample_df)

    return pd.concat(annotator_samples).reset_index()


def resolve_disagreements(df: pd.DataFrame, revisions: pd.DataFrame) -> pd.DataFrame:
    """Apply revision rows to a disagreement table."""

    required_cols = {
        "Code",
        "Annotator 1",
        "Annotation 1",
        "Annotator 2",
        "Annotation 2",
        "Revision",
    }

    if not isinstance(df.index, pd.MultiIndex):
        raise ValueError("df must use a MultiIndex with levels PersonID and Annotator.")

    if "PersonID" not in df.index.names or "Annotator" not in df.index.names:
        raise ValueError(
            "df index must contain levels named 'PersonID' and 'Annotator'."
        )

    if not isinstance(revisions, pd.DataFrame):
        raise ValueError("revisions must be a pandas DataFrame.")

    has_personid_col = "PersonID" in revisions.columns
    has_personid_index = revisions.index.name == "PersonID"
    if not has_personid_col and not has_personid_index:
        raise ValueError("revisions must include PersonID as a column or index.")

    missing_cols = required_cols - set(revisions.columns)
    if missing_cols:
        raise ValueError(f"revisions is missing required columns: {sorted(missing_cols)}")

    new_annotations = df.copy()
    if "Revised" not in new_annotations.columns:
        new_annotations["Revised"] = False

    def _coerce_revision_value(series: pd.Series, revision_val, pid, code):
        if pd.isna(revision_val):
            raise ValueError(f"Missing revision value for PersonID {pid}, code {code}.")

        non_missing = series.dropna()
        if non_missing.empty:
            return revision_val

        if pd.api.types.is_integer_dtype(non_missing):
            numeric_val = pd.to_numeric(revision_val, errors="raise")
            return int(numeric_val)

        if pd.api.types.is_float_dtype(non_missing):
            return float(pd.to_numeric(revision_val, errors="raise"))

        return str(revision_val).strip()

    for row_idx, row in revisions.iterrows():
        if pd.isna(row["Revision"]):
            continue

        pid = row["PersonID"] if has_personid_col else row_idx
        code = row["Code"]
        annotator_1 = row["Annotator 1"]
        annotator_2 = row["Annotator 2"]

        if pid not in new_annotations.index.get_level_values("PersonID"):
            raise ValueError(f"PersonID {pid} not found in df index.")

        if code not in new_annotations.columns:
            raise ValueError(f"Code {code} not found in df columns.")

        pid_annotators = set(new_annotations.xs(pid, level="PersonID").index)
        for annotator in (annotator_1, annotator_2):
            if annotator not in pid_annotators:
                raise ValueError(f"Annotator {annotator!r} not found for PersonID {pid}.")

        revision = _coerce_revision_value(new_annotations[code], row["Revision"], pid, code)

        for annotator in (annotator_1, annotator_2):
            new_annotations.loc[(pid, annotator), code] = revision

            one_hot_prefix = f"{code}_"
            one_hot_cols = [col for col in new_annotations.columns if col.startswith(one_hot_prefix)]
            if one_hot_cols and isinstance(revision, str):
                target_col = f"{one_hot_prefix}{revision}"
                if target_col not in one_hot_cols:
                    normalized_targets = {col.lower(): col for col in one_hot_cols}
                    target_col = normalized_targets.get(target_col.lower())

                if target_col is None or target_col not in one_hot_cols:
                    raise ValueError(
                        f"Revision {revision!r} does not map to one-hot columns for {code} (PersonID {pid})."
                    )

                new_annotations.loc[(pid, annotator), one_hot_cols] = 0
                new_annotations.loc[(pid, annotator), target_col] = 1

            new_annotations.loc[(pid, annotator), "Revised"] = True

    return new_annotations
