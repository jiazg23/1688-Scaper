# Validation status — October 19, 2026

**Development preview, not production-validated.**

## Confirmed locally

- Complete local suite: **59 tests passed**, including seven offline browser tests and
  seven regression cases for the supplied real product-detail page.
- Parsed all 60 unique product cards from the owner's supplied saved results.
- First captured product: ID `1071313125369`, displayed price `3.84`, MOQ `2`,
  supplier `Jieyang Jiayi Technology Co., Ltd.` and its captured storefront link.
- Currency is USD when the owner's selected header/dropdown is included.
  A standalone `$` card remains currency-unknown rather than assumed USD/CNY.
- Real detail fixture for the same offer parses `¥25.00`, two color variants
  with displayed stock 3/583, mixed-batch MOQ 2, 38 attributes, seven gallery
  images and aggregate product rating 5.0. Product rating is not supplier rating.
  Its ISO currency is unknown without explicit page settings; it does not
  inherit the search card's USD price. Login-gated completeness is explicit.
- Hidden rating containers are ignored; no verification/factory badge is inferred
  from unlabelled image assets or company names.
- Offline tests cover validation, tier arithmetic, MOQ boundaries, ambiguity,
  exports, private image addresses, deduplication, per-image limits and recovery.
- Seven offline Chromium tests pass: actual supplied search/upload selectors,
  changed-card pagination, disabled Next, unchanged-product rejection and
  terminal verification detection, plus hidden/active login UI regression cases.
  All outgoing requests are aborted.
- Fixed locally reproduced false positives from SDK script references to challenge
  paths and hidden login controls. Actual challenge URLs/titles/controls, standalone
  verification configurations and visible login forms remain terminal errors.
- Failure reports record stage and reason without raw page source, credentials
  or challenge URL tokens; diagnostic-write errors do not replace the original error.
- Startup import/default-input check, Python compilation and dependency check pass.
- Actor, input, dataset and output definitions pass the published
  [Apify JSON schemas](https://github.com/apify-projects/actor-json-schemas).
  The output schema omits the unsupported root `type` keyword.
- [GitHub's Linux validation](https://github.com/jiazg23/1688-Scaper/actions)
  passed the offline suite, Docker build, container import/startup check and
  Chromium startup with container networking disabled.

These are saved-HTML/local tests, not live search results.

## Pending or blocked

| Acceptance case | Status |
| --- | --- |
| Linux container build and offline browser startup | Passed in GitHub Actions; not an actual Apify run |
| Live keyword search returns relevant cards | Owner's first run failed in old access detector; actual cause needs new failure report |
| Live second page and final-page detection | Control logic tested offline only |
| Live image upload and image pagination | Selectors supplied; end-to-end unverified |
| Live multi-image results with independent limits | Runner tested with synthetic batches only |
| Public detail DOM and visible variants/stock | Captured-page regression tests pass; live access pending |
| Real quantity-price tiers | No source fixture; variant rows are not volume tiers |
| Currency/language in a fresh Apify browser session | Unverified; no forced USD/translation |
| Performance, proxy cost, commercial viability | Not measured |
| Apify build/startup | Owner's supplied live log confirms startup under limited permissions |
| Publishing/monetization | Not performed by this agent; current owner settings unverified |

## Initial access observations

Before the browser refusal, direct product and search requests returned
verification redirects, not product records. The homepage alone was reachable.
The browser's site-safety policy then rejected the challenge destination and
1688 browser access. No CAPTCHA was solved and no alternate access route was
used after that denial.

## Owner-reported Apify run

The October 19 log for build `HeWsquxXqMu3HdrwS` confirms successful container,
SDK and browser startup, followed by an `AccessBlocked` classification. That log
has no saved page evidence or specific detection reason, so it cannot establish
whether the page was a genuine challenge or one of the detector's reproduced
false positives. Version 0.1.1 adds precise stages and failure reports. No new
live 1688 request was performed by the development agent to test this change.

## Release acceptance

1. If volume quotes are required, supply real quantity-tier fixtures and verify
   their units and variant applicability before connecting the price calculator.
2. Verify regional layout, new-tab behavior and image-pagination selectors.
3. Keep the CI Docker build and offline suite passing.
4. Obtain permitted live validation for URL, keyword, multi-page and multi-image
   runs on the actual Apify build. Independently check output against source pages.
5. Confirm challenge/partial-failure reporting, recovery exports and default input.
6. Measure run cost and success rate before enabling Store monetization.

Do not infer production readiness from an all-green offline test suite.
