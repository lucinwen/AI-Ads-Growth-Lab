import pytest
from app.metrics import MetricRow, aggregate_metrics


def row(**overrides):
    values = dict(
        data_mode="SIMULATED", impressions=1000, clicks=20,
        landing_page_views=18, add_to_cart=5, purchases=2,
        refunded_orders=0, spend_usd=20.0, attributed_revenue_usd=60.0
    )
    values.update(overrides)
    return MetricRow(**values)


def test_aggregate_metrics_uses_aggregated_counts():
    result = aggregate_metrics([row(), row(impressions=1000, clicks=40, purchases=4,
                                           spend_usd=40.0, attributed_revenue_usd=120.0)])
    assert result["totals"]["impressions"] == 2000
    assert result["metrics"]["ctr"] == pytest.approx(0.03)
    assert result["metrics"]["cvr_click_to_purchase"] == pytest.approx(6 / 60)
    assert result["metrics"]["roas"] == pytest.approx(3.0)


def test_zero_denominators_return_none():
    result = aggregate_metrics([row(impressions=0, clicks=0, purchases=0, spend_usd=0,
                                     attributed_revenue_usd=0)])
    assert result["metrics"]["ctr"] is None
    assert result["metrics"]["cpc_usd"] is None
    assert result["metrics"]["roas"] is None


def test_simulated_and_real_cannot_mix():
    with pytest.raises(ValueError, match="cannot be mixed"):
        aggregate_metrics([row(), row(data_mode="REAL")])


def test_negative_values_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        aggregate_metrics([row(clicks=-1)])


def test_two_proportion_test_detects_large_difference():
    from app.metrics import compare_proportions
    result = compare_proportions(
        control_successes=100, control_trials=10000,
        treatment_successes=180, treatment_trials=10000,
        minimum_trials_per_arm=1000, mde_absolute=0.005,
    )
    assert result["decision"] == "PROMISING"
    assert result["p_value"] < 0.05
    assert result["absolute_difference"] == pytest.approx(0.008)
    assert result["planning"]["approx_required_sample_per_arm_80pct_power"] > 0


def test_two_proportion_test_marks_small_sample_inconclusive():
    from app.metrics import compare_proportions
    result = compare_proportions(
        control_successes=10, control_trials=100,
        treatment_successes=20, treatment_trials=100,
        minimum_trials_per_arm=1000,
    )
    assert result["decision"] == "INSUFFICIENT_SAMPLE"


def test_two_proportion_test_rejects_invalid_counts():
    from app.metrics import compare_proportions
    with pytest.raises(ValueError, match="successes"):
        compare_proportions(
            control_successes=101, control_trials=100,
            treatment_successes=20, treatment_trials=100,
        )
