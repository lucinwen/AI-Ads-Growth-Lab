# Data Dictionary

## Metric row grain
One row per date × experiment × variant × source. All counts are non-negative integers. Spend and attributed revenue use USD in the starter CSV; production storage should use integer cents plus ISO currency.

## Required fields
- date, experiment_id, channel, campaign_id, ad_group_id, creative_id, variant, data_mode
- impressions, video_2s_views, video_6s_views, clicks, landing_page_views
- add_to_cart, checkout_starts, purchases, orders_refunded
- spend_usd, attributed_revenue_usd

## Metric definitions
| Metric | Formula | Notes |
|---|---|---|
| CTR | clicks / impressions | impressions=0 → null |
| CPC | spend / clicks | clicks=0 → null |
| LPV rate | LPV / clicks | clicks=0 → null |
| ATC rate | ATC / LPV | LPV=0 → null |
| CVR | purchases / clicks | Explicitly click-to-purchase in V1 |
| CPA | spend / purchases | purchases=0 → null |
| AOV | attributed revenue / purchases | Revenue/order definition required |
| ROAS | attributed revenue / spend | Not profit; not ROI |
| Refund rate | refunded orders / purchases | Mature cohorts required |

## Production schema entities
Workspace, Brand, Product, Claim, AudienceHypothesis, Campaign, Creative, AssetVersion, Experiment, ExperimentVariant, MetricDaily, Event, AgentRun, ReviewRecord, AuditLog.

## Provenance
Each record carries data_mode = SIMULATED or REAL. A metric snapshot may contain only one mode. REAL requires source name, import timestamp, account timezone, attribution window, currency, export reference and authorization record.
