from __future__ import annotations

from dataclasses import dataclass, asdict
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
