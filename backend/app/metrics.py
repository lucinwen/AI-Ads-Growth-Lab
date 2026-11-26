from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Optional


@dataclass(frozen=True)
class MetricRow:
    data_mode: str
    impressions: int
    clicks: int
    landing_page_views: int
    add_to_cart: int
    purchases: int
    refunded_orders: int
    spend_usd: float
    attributed_revenue_usd: float


def _ratio(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0:
        return None
    return numerator / denominator


def aggregate_metrics(rows: Iterable[MetricRow]) -> dict:
    rows = list(rows)
    if not rows:
        raise ValueError("At least one metric row is required")

    modes = {r.data_mode for r in rows}
    if len(modes) != 1:
        raise ValueError("SIMULATED and REAL records cannot be mixed")
    mode = next(iter(modes))
    if mode not in {"SIMULATED", "REAL"}:
        raise ValueError("data_mode must be SIMULATED or REAL")

    count_fields = (
        "impressions", "clicks", "landing_page_views", "add_to_cart",
        "purchases", "refunded_orders"
    )
    for row in rows:
        for field in count_fields:
            value = getattr(row, field)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")
        if not isfinite(row.spend_usd) or not isfinite(row.attributed_revenue_usd):
            raise ValueError("Spend and attributed revenue must be finite numbers")
        if row.spend_usd < 0 or row.attributed_revenue_usd < 0:
            raise ValueError("Spend and attributed revenue must be non-negative")

    totals = {field: sum(getattr(r, field) for r in rows) for field in count_fields}
    spend = round(sum(r.spend_usd for r in rows), 2)
    revenue = round(sum(r.attributed_revenue_usd for r in rows), 2)

    metrics = {
        "ctr": _ratio(totals["clicks"], totals["impressions"]),
        "cpc_usd": _ratio(spend, totals["clicks"]),
        "lpv_rate": _ratio(totals["landing_page_views"], totals["clicks"]),
        "atc_rate": _ratio(totals["add_to_cart"], totals["landing_page_views"]),
        "cvr_click_to_purchase": _ratio(totals["purchases"], totals["clicks"]),
        "cpa_usd": _ratio(spend, totals["purchases"]),
        "aov_usd": _ratio(revenue, totals["purchases"]),
        "roas": _ratio(revenue, spend),
        "refund_rate": _ratio(totals["refunded_orders"], totals["purchases"]),
    }
    return {
        "data_mode": mode,
        "row_count": len(rows),
        "totals": {**totals, "spend_usd": spend, "attributed_revenue_usd": revenue},
        "metrics": metrics,
        "interpretation_guardrails": [
            "ROAS is attributed revenue divided by ad spend; it is not ROI or profit.",
            "Synthetic data is not evidence of real campaign performance.",
            "Rates are calculated from aggregated counts, not averaged row-level rates.",
        ],
    }


def _normal_cdf(value: float) -> float:
    from math import erf, sqrt
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def proportion_confidence_interval(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion."""
    if trials <= 0:
        return None
    from math import sqrt
    p = successes / trials
    denominator = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denominator
    margin = z * sqrt((p * (1.0 - p) + z * z / (4.0 * trials)) / trials) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def compare_proportions(
    *,
    control_successes: int,
    control_trials: int,
    treatment_successes: int,
    treatment_trials: int,
    alpha: float = 0.05,
    minimum_trials_per_arm: int = 1000,
    mde_absolute: float | None = None,
) -> dict:
    """Two-sided pooled two-proportion z-test with Wilson arm intervals.

    Intended for randomized binary outcomes. Observational or synthetic data
    must not be interpreted as causal evidence.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")
    for label, successes, trials in (
        ("control", control_successes, control_trials),
        ("treatment", treatment_successes, treatment_trials),
    ):
        if not isinstance(successes, int) or not isinstance(trials, int):
            raise ValueError(f"{label} counts must be integers")
        if trials <= 0 or successes < 0 or successes > trials:
            raise ValueError(f"{label} requires 0 <= successes <= trials and trials > 0")
    if mde_absolute is not None and not 0 < mde_absolute < 1:
        raise ValueError("mde_absolute must be between 0 and 1")

    from math import sqrt
    p_control = control_successes / control_trials
    p_treatment = treatment_successes / treatment_trials
    difference = p_treatment - p_control
    pooled = (control_successes + treatment_successes) / (control_trials + treatment_trials)
    standard_error = sqrt(pooled * (1.0 - pooled) * (1.0 / control_trials + 1.0 / treatment_trials))
    if standard_error == 0:
        z_score = 0.0
        p_value = 1.0
    else:
        z_score = difference / standard_error
        p_value = 2.0 * (1.0 - _normal_cdf(abs(z_score)))

    z_critical = 1.959963984540054
    se_difference = sqrt(
        p_control * (1.0 - p_control) / control_trials
        + p_treatment * (1.0 - p_treatment) / treatment_trials
    )
    difference_ci = [difference - z_critical * se_difference, difference + z_critical * se_difference]
    relative_lift = difference / p_control if p_control > 0 else None

    if control_trials < minimum_trials_per_arm or treatment_trials < minimum_trials_per_arm:
        decision = "INSUFFICIENT_SAMPLE"
    elif p_value < alpha and difference > 0:
        decision = "PROMISING"
    elif p_value < alpha and difference < 0:
        decision = "UNDERPERFORMING"
    else:
        decision = "INCONCLUSIVE"

    required_per_arm = None
    if mde_absolute is not None and 0 < p_control < 1:
        p_alt = min(0.999999, max(0.000001, p_control + mde_absolute))
        p_bar = (p_control + p_alt) / 2
        required_per_arm = int(
            ((1.959963984540054 * sqrt(2 * p_bar * (1 - p_bar))
              + 0.8416212335729143 * sqrt(p_control * (1 - p_control) + p_alt * (1 - p_alt))) ** 2)
            / (mde_absolute ** 2)
        ) + 1

    return {
        "control": {"successes": control_successes, "trials": control_trials, "rate": p_control,
                    "wilson_95_ci": proportion_confidence_interval(control_successes, control_trials)},
        "treatment": {"successes": treatment_successes, "trials": treatment_trials, "rate": p_treatment,
                      "wilson_95_ci": proportion_confidence_interval(treatment_successes, treatment_trials)},
        "absolute_difference": difference,
        "relative_lift": relative_lift,
        "difference_95_ci": difference_ci,
        "z_score": z_score,
        "p_value": p_value,
        "alpha": alpha,
        "decision": decision,
        "planning": {"mde_absolute": mde_absolute, "approx_required_sample_per_arm_80pct_power": required_per_arm},
        "interpretation_guardrails": [
            "A p-value is not the probability that the null hypothesis is true.",
            "Do not stop early or repeatedly peek without a pre-registered sequential-testing plan.",
            "Random assignment and comparable delivery are prerequisites for causal interpretation.",
            "Synthetic or observational data cannot establish causal campaign lift.",
            "The sample-size estimate is approximate and assumes independent binary outcomes and equal allocation.",
        ],
    }
