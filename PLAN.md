# 1688 Product & Supplier Finder — execution plan

## Current scope

An independent Apify Actor with two automatic input paths:
**keywords** or **numeric Offer IDs**. IDs take priority; no mode dropdown.
Image search, search-results links and full product URL inputs are removed at
the owner's request.

Keep supported extraction, independent per-keyword quotas, product deduplication,
supplier shortlist exports, failure diagnostics and recovery snapshots.
Use explicit Apify residential proxy configuration with one selected CN/HK
country/session per run. Do not retry access denials with a different identity.

## Implementation

- Input schema: clear keyword/ID instructions and limits, explicit chargeable
  proxy settings, CSV defaults on.
- Input validation: numeric IDs, ID precedence, safe filenames, bounded quotas,
  migration aliases for older keyword clients and explicit removed-mode errors.
- Collector: ordinary homepage keyword entry/new-tab handling, Next-page checks,
  public detail retrieval with exact ID matching.
- Proxy initialization: RESIDENTIAL group, explicit country, one session,
  no credentials in logs and no silent country/direct fallback.
- Exports: one dataset product row, source inputs, separate supplier CSV,
  page checkpoints and terminal access-error diagnostics.

## Verified offline

85 regression tests pass, including 22 local browser tests and seven mocked
proxy tests. Saved source HTML supports 60 product cards and the provided
detail page. No test contacts 1688 or creates paid proxy traffic.
Actor definitions and container startup are validated before delivery.

## Historical decisions

- Owner supplied keyword controls, pagination, 60 result cards, selected USD
  settings and a public detail-page capture.
- Initial release added keyword/image/direct-detail paths; optional-popup and
  new-tab logic were later regression-tested.
- Version 0.1.2 introduced copied search-results links and removed direct URL mode.
- Owner's live logs then showed a homepage login redirect and a search-link
  verification frame. Successful startup did not establish successful scraping.
- Research found competitor documentation describing other access methods and
  country-specific residential proxies; their underlying source was not public.
- Owner requested only keyword/Offer ID inputs and Apify-managed proxy billing.
- Version 0.2.0 removes image/search-link paths, restores numeric-ID detail
  collection and implements explicit residential-country configuration.

## Remaining work / release gate

- Successful permitted live collection for both current input paths on Apify.
- Verification of selected-country proxy access and actual traffic/compute costs.
- Multi-keyword and second-page acceptance against current source results.
- Exact optional-login X markup if real popup dismissal still needs adjustment.
- Quantity-tier fixtures before any firm bulk-quote feature.
- Pricing, public publication and monetization only after reliable live evidence
  and an explicit launch decision.

The development browser denied 1688 access. Do not route around that tool
restriction through another domain, proxy, private API or browser surface.
No competitor Actor is called and no paid tests or billing changes are authorized
by the offline build workflow.
