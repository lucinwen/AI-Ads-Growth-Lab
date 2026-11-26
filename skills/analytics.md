# Paid Media Experiment Analytics

## Metric definitions
CTR=clicks/impressions; CPC=spend/clicks; CVR=purchases/clicks; CPA=spend/purchases; AOV=attributed_revenue/purchases; ROAS=attributed_revenue/ad_spend.

ROI requires incremental profit and total investment. Never use ROAS as ROI.

## Rules
- Check event definitions, attribution window, currency, timezone, missingness, duplicates and data_mode.
- Zero denominator => null/N/A.
- Aggregate counts before calculating rates.
- Separate descriptive differences from statistically supported conclusions.
- Require baseline, MDE, alpha, power and sample-size plan before inferential claims.
- Never mix SIMULATED and REAL records in one metric snapshot.
- Do not claim causal lift without appropriate randomization and measurement.

## Output
data_quality_report, metric_snapshot, funnel_diagnostics, uncertainty, limitations, recommended_next_tests.
