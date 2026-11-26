# Experiment Plan — EXP-US-BEAUTY-001

## Experiment objective
Validate the product workflow and analytics implementation using synthetic records. This experiment does **not** establish real market performance or causal lift.

## Demo product
Luma Dew Daily Barrier Moisturizer — fictional brand/product for portfolio demonstration only. No real consumer data, brand assets, testimonials, or clinical claims are used.

## Market and channel
United States; TikTok-style vertical short-video placement. The channel label in the seed data is illustrative, not a platform export.

## Creative hypotheses
| Variant family | Angle | Hook | Hypothesis |
|---|---|---|---|
| A | Routine / everyday | “A simple step in my morning routine.” | Routine framing may fit naturally into an everyday skincare routine. |
| B | Texture / sensory | “A closer look at the texture.” | A close-up product demonstration may increase qualified curiosity. |
| C | Product education | “What is in my daily moisturizer?” | Fact-based education may improve product understanding. |
| D | Creator-style walkthrough | “Here is how the product fits into my routine.” | Creator-style delivery may improve attention and comprehension. |

Hooks are draft creative prompts, not verified product claims or genuine testimonials. Validate all claims against product evidence before external use.

## Design
- 4 concept families × 3 versions = 12 creative records.
- Synthetic daily rows across 7 dates.
- Primary metrics: CTR and click-to-purchase CVR; interpret separately.
- Secondary: CPC, LPV rate, ATC rate, CPA, AOV, ROAS, 2s/6s view counts, refund rate.
- Controls for a real test: same product, price, offer, landing page, audience definition, placement, optimization event, schedule, and attribution window.
- Real experiments require platform randomization where available, pre-registered MDE, baseline rate, alpha, power, sample size, and stopping rule.

## Synthetic data warning
All starter records are generated for software validation. They are not actual TikTok or Meta delivery logs, not real customer behavior, and not evidence of CTR/CVR/ROAS/GMV improvement. Any dashboard or case study must retain a prominent SIMULATED label.

## Analysis rules
1. Aggregate counts first, then calculate rates. Do not average daily CTRs without weighting.
2. Zero denominator → N/A.
3. CTR and CVR answer different questions.
4. High CTR with low CVR can indicate message/landing-page mismatch, poor traffic quality, offer friction, or tracking issues; investigate before concluding.
5. ROAS is attributed revenue divided by ad spend; it is not profit or ROI.
6. If data is insufficient, report INCONCLUSIVE rather than declaring a winner.
7. Descriptive differences in synthetic data are not causal evidence.
