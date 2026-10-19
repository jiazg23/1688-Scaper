# Private build and release checklist

## Source

Repository: https://github.com/jiazg23/1688-Scaper
Branch: `main`; source directory: `.`; definition: `.actor/actor.json`.
Version 0.2.2 uses keywords or numeric Offer IDs only. IDs take priority.
No saved browser session, token or personal credentials belong in this repository.

## Build privately first

1. Build the latest source and confirm Actor/input/dataset/output definitions load.
2. Confirm the container's `python -m src.main --check` succeeds.
3. Check RESIDENTIAL proxy access and selected-country availability in Apify Console.
   China (CN) is the default; Hong Kong (HK) is a separate explicit choice.
4. Choose a spending cap and timeout before testing. Residential traffic incurs
   charges through Apify; failed requests can still consume traffic.
5. Test one keyword, five products and one page; separately test one known Offer ID.
6. Inspect actual rows, currency, MOQ, source links, partial flags and run summary.

The agent has not started paid tests, purchased proxies or changed monetization.
Proxy country selection alone is not evidence that the previous access errors
are resolved. No automatic fallback or country/identity retry is implemented.

## Migration

- Replace `searchTerms` with `keywords` in new integrations. The old keyword
  aliases remain supported when new fields are absent.
- Replace the old per-keyword limits with `maxResults` and `maxPagesPerKeyword`.
- Remove image/search-link inputs. They now raise explicit validation errors.
- Provide numeric `offerIds`, not full URLs; these skip all keyword searches.
- The competitor's `rotate` setting, sorting filters and paid add-ons are not
  supported options in this independent Actor.

## Evidence still needed

- Successful permitted live keyword, multi-keyword and second-page collection.
- Version 0.2.2 supports the domestic control pair in the owner's latest failure
  inventory. If entry/submission fails again, obtain `search_controls` and
  `search_buttons`; the exact observed button class may have changed.
- Domestic result-card/pagination HTML if the next run reaches an unsupported
  results layout. Only global result cards are currently source-backed.
- Successful permitted live Offer ID extraction against the saved source layout.
- Whether available CN/HK residential access works in this account and at what cost.
- Real surrounding X markup for the optional login iframe; current close-button
  test wrappers are synthetic.
- Quantity-tier examples if future bulk quotations are required.

The development browser previously denied 1688 access. Do not retry through
alternate domains, private APIs, proxies or other surfaces to circumvent that
tool policy. Saved-page development and mocked configuration tests remain possible.

## Before public release

- Complete all live acceptance cases in VALIDATION.md on the actual Apify build.
- Confirm ordinary limited-permission startup and accurate failure/recovery output.
- Measure cost, speed, relevant unique results and failure rate over multiple runs.
- Set pricing only after measuring residential traffic and compute costs.
- Explicitly choose publication, monetization, platform timeouts and cost caps.
- Keep preview warnings until production readiness is supported by evidence.

## Preview display information

Name: **1688 Wholesale Product & Supplier Finder**

Description:

> Development preview: search 1688 by keywords or numeric Offer IDs. Collect
> supported product and supplier fields, displayed prices, MOQs and CSV exports.
> Explicit residential proxy country settings; traffic costs apply. Live access
> is not yet release-validated.

Do not advertise guaranteed access, complete verification reports, all supplier
intelligence, automatic translation or an independently validated competitor
implementation.
