# Creative Asset QA

Review technical quality and brand/creative consistency before an asset enters testing.

## Dimensions
- Format, aspect ratio, resolution, duration and platform safe zones
- Subtitle readability, spelling, audio levels and visual continuity
- Product/packaging accuracy and brand consistency
- Hook clarity, offer visibility and CTA legibility
- Landing-page consistency and asset rights metadata

## Rules
- Score dimensions separately; do not hide hard failures in an average score.
- Distinguish machine-checkable issues from subjective human review.
- Record timestamps/frame references for video issues.
- Never mark an asset ready if compliance status is BLOCK or NEEDS_REGULATORY_REVIEW.

## Output
qa_scorecard, hard_failures[], human_review_questions[], ready_status.
