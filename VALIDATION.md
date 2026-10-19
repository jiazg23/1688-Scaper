# Validation status — October 19, 2026

**Version 0.3.0 — development preview, not production-validated.**

## Confirmed offline

- **123 tests pass:** 44 core/parser/input/runner tests, 35 local Chromium tests,
  12 access-diagnostic tests, seven mocked proxy tests and 25 synthetic API tests.
- Optional documented Elim search/Offer-ID adapter: owner activation/approval
  gates, secret handling, unpaid-user gate, whole-run attempted-request limit,
  result spending allowance, sequential pacing, endpoint allowlist, no redirects,
  sanitized errors, partial exports and no automatic browser/proxy fallback.
  These tests use synthetic documented-shape responses, NOT real provider data.
- The form exposes keywords and numeric Offer IDs, not a mode dropdown.
  IDs take priority even when the example keyword is still filled.
- Image search, image downloading and search-results-link collection are removed
  from the input and runtime. Removed inputs fail explicitly instead of running
  the sample keyword.
- Per-keyword product/page caps reset independently; repeated products preserve
  all matching inputs while appearing once in the dataset.
- Saved keyword controls, same/new results tabs, changed-card pagination,
  disabled Next, repeated-page rejection and page-level recovery are tested.
- The Offer ID collector opens only the canonical public page for the requested
  numeric ID. Detail identity must match; recommendations do not satisfy it.
- All 60 real saved search cards parse. First product: 1071313125369, displayed
  price 3.84, MOQ 2, supplier Jieyang Jiayi Technology Co., Ltd.
- Currency is USD only when the owner's selected USD header/dropdown is present.
  A standalone dollar symbol does not establish USD or CNY.
- The real detail fixture parses a displayed ¥25.00, two color variants with
  stock 3/583, mixed-batch MOQ 2, 38 attributes, seven gallery images and product
  rating 5.0. This is not supplier rating or a quantity-discount ladder.
- Detail ISO currency remains unknown without explicit source evidence.
  Login-gated completeness is flagged rather than fabricated.
- Proxy mocks confirm the RESIDENTIAL group, explicit CN/HK selection, one
  session initialization, decoded credentials without logging, and sanitized
  access/configuration errors without direct/country fallback.
- Known search controls are chosen by visibility, enabled/editable state, not
  the first DOM match. Hidden/read-only copies, open shadow roots, unknown
  controls and sanitized failure inventories are regression-tested. Actual form
  values, passwords, event handlers, scripts and URLs are not exported by the inventory.
- The domestic input/button attributes from FAILURE_01 (3).json are recognized
  and paired separately from global controls. Offline regressions cover entry,
  submission, hidden global copies, unrelated buttons, changed-class rejection
  and visible verification. Result transitions use the old global card fixture;
  these are not domestic result-parser tests.
- Login/verification and HTTP 401/403/429 remain terminal across the batch.
  Optional login closure requires a real close control and usable public content.
- Local Chromium tests abort all outgoing network requests; proxy tests mock the
  SDK. No live 1688 or paid proxy request is made by these tests.

## Build checks

Startup imports/default input and Python compilation pass locally. The four
Actor definition files are checked against Apify's published schemas before
upload. GitHub Actions is configured to build the Linux Docker image and check container imports
and Chromium startup with container networking disabled.

Current Docker CI completion must be checked separately; earlier 0.2.x jobs were
queued at delivery. These are build/offline checks, not live site acceptance.

## Live evidence and remaining acceptance

| Case | Status |
| --- | --- |
| Apify container/SDK/browser startup under limited permissions | Owner logs confirm earlier versions start successfully |
| Keyword collection on the earlier generic proxy setup | Failed at opening_homepage; login.taobao.com was the final host |
| Search-link mode in version 0.1.2 | Owner run detected a visible verification frame; mode is now removed |
| Residential proxy configuration | Owner's HK run initialized and fetched the homepage; actual exit-IP geolocation and CN access unverified |
| HK keyword run in 0.2.0 | Reached HTTP-200 homepage, then timed out at entering_keyword; known input absent from captured main HTML |
| HK keyword run in 0.2.1 | Failure inventory identifies domestic input and button, both visible and usable |
| HK keyword run in 0.2.2 | Entered and submitted keyword, then CAPTCHA Verification at s.1688.com; zero cards |
| Optional Elim API collection in 0.3.0 | Disabled; no account/key, written approval, trial or live response validated |
| Provider billing and public Apify result pricing | Not activated or changed; provider invoice remains separate |
| Successful live Offer ID collection in 0.2.2 | Not tested |
| Exact optional-popup X wrapper | Not supplied; test wrappers are synthetic |
| Real quantity-price tiers | No source fixture; not connected |
| Current relevance, speed, proxy traffic cost and success rate | Not measured |
| Publishing/monetization | Not changed by the agent |

The earlier homepage failure report contains stage opening_homepage, code
login_url, host login.taobao.com, zero product cards and no keyword input.
The subsequent search-link log reports verification_frame. Neither establishes
that every manual visitor needs an account; both show this Actor's earlier
browser sessions failed before collection.

The newer `FAILURE_01 (3).json` records www.1688.com, title 阿里1688首页,
HTTP 200 and stage entering_keyword. Its inventory identifies the domestic
textarea ID/name and exact button class now supported in 0.2.2. This resolves
the observed selector mismatch offline, not the end-to-end live release gate.
No domestic result HTML was supplied. The exact captured button class may change
with a website deployment; unknown buttons are not guessed.

The subsequent report (4) identifies a genuine verification URL after successful
submission. No change suppresses that restriction. The API preparation uses only
published third-party service documentation and mocks; it makes no live requests.
Provider response-envelope/pagination semantics, currency, freshness, reliability
and redistribution rights remain acceptance requirements, not established facts.

## Development access limitation

Before the browser refusal, live product/search probes returned verification
redirects; only the homepage was reachable. Browser policy subsequently denied
1688 access. No CAPTCHA was solved and no alternative domains, proxy routes,
private APIs or browser surfaces were used to circumvent that denial.

Version 0.2.0 changes input routing and standard initial proxy configuration.
The competitor's public input schema is not its underlying source code. No
claim is made that their private collection method has been reproduced.

## Release gate

1. Obtain permitted live validation on the actual private Apify build for keywords,
   Offer IDs, pagination, deduplication and partial-failure exports.
2. Confirm available proxy-country access and measure residential traffic costs,
   including failed attempts, before setting event prices.
3. Independently compare returned products and price/currency evidence with source.
4. Keep CI, definition schemas and ordinary limited-permission startup passing.
5. Keep preview warnings until successful live runs support removing them.

Do not infer production readiness from an all-green offline test suite.
