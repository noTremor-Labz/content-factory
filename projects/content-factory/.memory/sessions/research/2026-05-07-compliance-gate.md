# Research: Phase 3 Compliance Gate

**Date:** 2026-05-07
**Task size:** M/L slice

## Question

How should Content Factory add the first compliance gate for a regulated vape/nicotine-adjacent pilot without overbuilding a legal rules platform?

## Local Findings

- Existing lifecycle is `draft -> planned -> review -> approved/rework`.
- Export/package creation currently gates only on:
  - `RenderJob.status == succeeded`
  - `ContentItem.status == approved`
- Worker package processing repeats the same content/render gate, which is good defense-in-depth.
- Review approval currently has no compliance context; any owner/reviewer can approve an open review task.
- Web cockpit has review/export routes but no compliance data in `CockpitData`.
- Business context explicitly says:
  - pilot is native/lifestyle content, not direct nicotine product advertising;
  - product placement can still be interpreted as promotion;
  - MVP rules should block direct CTA, youth-coded aesthetics, health/status claims, product-use demos, and store a risk score/reason.

## Current External Policy Signals

Sources checked on 2026-05-07:

- FDA ENDS overview: FDA regulates manufacture, import, packaging, labeling, advertising, promotion, sale, and distribution of ENDS components/parts; FDA also highlights youth-use prevention and says non-users should not start using e-cigarettes.
  - https://www.fda.gov/tobacco-products/products-ingredients-components/e-cigarettes-vapes-and-other-electronic-nicotine-delivery-systems-ends
- FDA advertising/promotion: covered tobacco ads require warning statements; modified-risk descriptors like "light", "mild", "low" require an MRTP order; free samples are prohibited.
  - https://www.fda.gov/tobacco-products/products-guidance-regulations/advertising-and-promotion
- FDA covered tobacco warning page: ENDS warning requirements remain in scope; nicotine warning statement is required for covered tobacco products.
  - https://www.fda.gov/tobacco-products/labeling-and-warning-statements-tobacco-products/covered-tobacco-products-and-roll-your-own-cigarette-tobacco-labeling-and-warning-statement
- Google Ads tobacco policy: ads for tobacco, tobacco components/facilitation, and simulated smoking products such as e-cigarettes are not allowed.
  - https://support.google.com/adspolicy/answer/16489929?hl=en
- TikTok Ads dangerous products policy: ad content and landing pages may not show, promote, or sell tobacco, nicotine, or related products; anti-smoking/quitting support may be allowed.
  - https://ads.tiktok.com/help/article/tiktok-ads-policy-dangerous-products-or-services?lang=en
- X tobacco policy: global promotion is generally prohibited with limited pre-authorized/local-law exceptions; smoking alternatives require age/regulatory restrictions.
  - https://business.x.com/en/help/ads-policies/ads-content-policies/tobacco-and-tobacco-accessories
- FTC/FDA warning letters on flavored e-liquid influencer posts: failure to disclose nicotine risk and material influencer relationships can create FTC/FDA concerns.
  - https://www.ftc.gov/news-events/news/press-releases/2019/06/ftc-fda-send-warning-letters-companies-selling-flavored-e-liquids-about-social-media-endorsements

## Alternatives Considered

1. **Manual-only review notes**
   - Pros: fastest.
   - Cons: no systemic memory, no risk score, no machine-readable gate, export can be approved by habit.

2. **Full policy engine with admin-authored rules and visual editor**
   - Pros: flexible long term.
   - Cons: too much for first pilot slice; invites unreviewed policy edits before legal review.

3. **Deterministic first-pass engine with persisted default rules/checks and human override for soft flags**
   - Pros: auditable, testable, conservative, minimal dependencies, aligns with human-in-the-loop.
   - Cons: keyword rules are not legal review and will need tuning.

## Recommendation

Use option 3.

Add persisted `ComplianceRule` and `ComplianceCheck` records, but keep the first rule set code-owned and seeded idempotently. Run checks when content enters review and expose a manual rerun endpoint. Review approval must require the latest check. Hard failures block approval. Soft flags require an explicit reviewer override reason. Export/package and worker packaging must verify the approved content has a final compliance decision so legacy rows cannot bypass the gate.
