# Product Requirements — AI Ads Growth Lab

**Version:** 1.0 · **Owner:** 文欣璐 · **Market:** United States · **Vertical:** Beauty & Skincare

## 1. Product vision
A standalone AI-agent workspace connecting beauty-ad creative strategy, multimodal asset production, claim/compliance precheck, experiment measurement, and evidence-based iteration.

## 2. Problem
- Creative briefs, scripts, assets, versions, and media results are fragmented.
- Creative quality is often judged subjectively without a consistent rubric.
- Creative production is disconnected from click-to-purchase funnel outcomes.
- Learnings and failure cases are not systematically fed into the next creative cycle.
- Beauty advertising needs claim substantiation, rights tracking, and landing-page consistency.

## 3. Users
Brand/growth lead; creative strategist; designer/video creator; media buyer/analyst; product/project owner.

## 4. V1 goals
1. Store workspace, product facts, approved claims, creative concepts, assets, experiments, and metric records.
2. Generate structured creative briefs and variants through specialist agents (staged).
3. Require evidence mapping for objective claims and human approval for high-risk content.
4. Import CSV records with explicit SIMULATED or REAL provenance.
5. Calculate CTR, CPC, LPV rate, ATC rate, CVR, CPA, AOV, ROAS deterministically.
6. Produce funnel diagnostics and next-test recommendations with uncertainty and limitations.
7. Keep agent runs, prompts, model versions, and approvals auditable.

## 5. Non-goals
- Autonomous campaign publishing or budget changes.
- Guaranteeing sales lift or ad approval.
- Legal advice or automated legal clearance.
- Claiming simulated metrics as actual campaign performance.
- Cross-platform causal attribution without a valid measurement design.

## 6. Core workflow
1. Create workspace and set immutable data mode.
2. Enter brand/product facts, offer, landing page, approved claims, evidence, and asset rights.
3. Create audience hypotheses and campaign brief.
4. Generate differentiated creative concepts (hook, angle, narrative, CTA, format, test variable).
5. Generate scripts/storyboards/prompts and register immutable asset versions.
6. Run compliance and technical QA; human reviewer approves.
7. Pre-register experiment hypothesis, variants, primary metrics, guardrails, MDE, sample size, schedule, and spend cap.
8. Import CSV; validate schema, duplicates, timezone, currency, attribution window, and data mode.
9. Calculate metrics in code; analytics agent explains results and limitations.
10. Human approves next creative test or media action.

## 7. Functional requirements
| ID | Requirement | Acceptance |
|---|---|---|
| FR-01 | Workspace + data mode | SIMULATED and REAL isolated |
| FR-02 | Product facts + claims | Every objective claim has evidence or remains unverified |
| FR-03 | Creative brief | Stores audience hypothesis, goal, channel, format, message and CTA |
| FR-04 | Creative variants | Each variant has distinct hypothesis and test variable |
| FR-05 | Asset registry | Version, hash, prompt, model, rights and source lineage |
| FR-06 | Compliance review | BLOCK / NEEDS_REVIEW / PASS; human approval gate |
| FR-07 | Experiment builder | Pre-registers hypothesis, variants, metrics and guardrails |
| FR-08 | CSV import | Type checks, duplicate detection, provenance, error report |
| FR-09 | Metric engine | Deterministic formulas and null for zero denominator |
| FR-10 | Analytics | Separates descriptive difference from causal conclusion |
| FR-11 | Audit log | Records agent runs, inputs, outputs, tools and approvals |
| FR-12 | Export | Report includes data mode, time window, metric definitions and caveats |

## 8. Primary metrics
- CTR = clicks / impressions
- CPC = spend / clicks
- LPV rate = landing_page_views / clicks
- ATC rate = add_to_cart / landing_page_views
- CVR = purchases / clicks (must state denominator)
- CPA = spend / purchases
- AOV = attributed_revenue / purchases
- ROAS = attributed_revenue / spend
- ROI is not ROAS. ROI requires incremental profit and total investment.

Zero denominators return null/N/A. Revenue definition, refund treatment, attribution window, timezone, and currency must be explicit.

## 9. V1 safety and trust
- SIMULATED data is visibly watermarked and cannot be mixed with REAL data.
- Claims: VERIFIED, UNVERIFIED, PROHIBITED, NEEDS_REVIEW.
- Never invent testimonials, clinical results, dermatologist endorsements, or before/after outcomes.
- Check ad-to-landing-page consistency and rights for music, fonts, talent, trademarks, and footage.
- No agent can publish an ad or alter spend in V1.
- LLMs do not calculate authoritative metrics; deterministic code does.

## 10. Success criteria
- Clean-machine startup documented.
- Synthetic sample CSV imports and aggregates correctly.
- Unit tests cover zero denominators, negative values, duplicate keys, and mode mismatch.
- One end-to-end demo can show brief → creative variants → review → experiment → metrics → next-test recommendation.
- Portfolio artifacts explicitly distinguish implemented features, simulated experiments, and future integrations.
