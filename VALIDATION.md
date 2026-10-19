# Validation status — October 19, 2026

**Development preview, not production-validated.**

## Confirmed locally

- Complete local suite: **38 tests passed**, including five offline browser tests.
- Parsed all 60 unique product cards from the owner's supplied saved results.
- First captured product: ID `1071313125369`, displayed price `3.84`, MOQ `2`,
  supplier `Jieyang Jiayi Technology Co., Ltd.` and its captured storefront link.
- Currency is USD when the owner's selected header/dropdown is included.
  A standalone `$` card remains currency-unknown rather than assumed USD/CNY.
- Hidden rating containers are ignored; no verification/factory badge is inferred
  from unlabelled image assets or company names.
- Offline tests cover validation, tier arithmetic, MOQ boundaries, ambiguity,
  exports, private image addresses, deduplication, per-image limits and recovery.
- Five offline Chromium tests pass: actual supplied search/upload selectors,
  changed-card pagination, disabled Next, unchanged-product rejection and
  terminal verification detection. All outgoing requests are aborted.
- Startup import/default-input check, Python compilation and dependency check pass.

These are saved-HTML/local tests, not live search results.

## Pending or blocked

| Acceptance case | Status |
| --- | --- |
| Apify/Linux container build and browser startup | CI configured; local Docker daemon unavailable |
| Live keyword search returns relevant cards | Blocked by development browser site-safety policy |
| Live second page and final-page detection | Control logic tested offline only |
| Live image upload and image pagination | Selectors supplied; end-to-end unverified |
| Live multi-image results with independent limits | Runner tested with synthetic batches only |
| Direct product details, variants and real quantity tiers | Product-detail sample still needed |
| Currency/language in a fresh Apify browser session | Unverified; no forced USD/translation |
| Performance, proxy cost, commercial viability | Not measured |
| Apify Actor created/published/monetized | Not performed |

## Initial access observations

Before the browser refusal, direct product and search requests returned
verification redirects, not product records. The homepage alone was reachable.
The browser's site-safety policy then rejected the challenge destination and
1688 browser access. No CAPTCHA was solved and no alternate access route was
used after that denial.

## Release acceptance

1. Supply real detail-page/price-tier fixtures and implement their exact adapter.
2. Verify regional layout, new-tab behavior and image-pagination selectors.
3. Pass the CI Docker build and offline suite.
4. Obtain permitted live validation for URL, keyword, multi-page and multi-image
   runs on the actual Apify build. Independently check output against source pages.
5. Confirm challenge/partial-failure reporting, recovery exports and default input.
6. Measure run cost and success rate before enabling Store monetization.

Do not infer production readiness from an all-green offline test suite.
