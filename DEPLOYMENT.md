# Private build and release checklist

## Source

Repository: https://github.com/jiazg23/1688-Scaper
Branch: `main`; source directory: `.`; definition: `.actor/actor.json`.
Version 0.3.0 uses keywords or numeric Offer IDs only. IDs take priority.
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

## Optional Elim API backend — not activated

The adapter is prepared, not enabled. Do not rebuild expecting the CAPTCHA to
disappear: the default remains the existing browser backend. No provider account,
API key, commercial permission, trial or billing setup has been obtained by the agent.

Before activation, obtain written permission specifically covering a paid public
Apify Actor, multiple customers, product-data redistribution and retained JSON/CSV
downloads. Confirm data-supply authorization, quota terms, pagination semantics,
pricing differences and permitted caching. Having an API key is not that permission.

After permission and an account are in place, the OWNER can configure these
environment variables in the private Actor. Never put keys in public input,
source files, screenshots, logs or chat:

| Owner variable | Purpose |
| --- | --- |
| `PRODUCT_DATA_SOURCE=elim` | Explicitly select the documented API. Default is `browser`. |
| `ELIM_COMMERCIAL_USE_APPROVED=true` | Owner attestation that written approval covers this use. Not proof supplied by the code. |
| `ELIM_API_KEY` | Provider key, stored using Apify's secret environment-variable settings. |
| `ELIM_MAX_REQUESTS_PER_RUN=5` | Shared cap across all keywords/IDs, counting failed attempts too; allowed 1–100. |
| `ELIM_ALLOW_UNPAID_RUNS=true` | Optional owner-funded preview/testing opt-in. Default blocks unpaid/unknown-plan users on Apify. |

API mode does not initialize Chromium, Apify Proxy or a fallback browser. Only
the fixed HTTPS provider host and documented search/find paths are used. Redirects,
automatic retries and inherited HTTP proxy settings are disabled. Requests are
sequential and paced at least 2.1 seconds apart; stricter account limits still apply.
Provider errors stop the batch and preserve previous collected products. The
run summary reports request attempts/cap but never key, response body or headers.

Start with one keyword, five results and one page after activation. Confirm the
actual response matches the documented direct product or `{items, paginate}`
contract; an unexpected wrapper is rejected, not guessed. Pagination currently
treats `total` as item count and requires matching `current` and numeric `size`.
Missing metadata leaves products partial unless a configured limit already ended
collection. No live response fixture has yet established these semantics.

### Customer billing versus provider billing

Customers can pay through Apify's per-result dataset event. Configure the existing
`apify-default-dataset-item` event and price in Publishing; this code does not set
prices or activate monetization. PPE mode requires a positive dataset event price
before any API call. It checks the result allowance and limits emitted unique rows.
The owner request cap is a separate external-cost safeguard, not a dollar guarantee.

You still pay Elim separately. Apify does not settle that provider invoice. Budget
for failed/empty calls, unused subscriptions, Apify commission and platform usage.
Free Apify users can consume provider credit without generating creator revenue;
keep the unpaid-run opt-in off until you explicitly fund and limit previews.

No custom start/search-call fee is added and no second charge is made for CSVs or
the supplier summary. Only an enabled dataset event charges dataset product rows.
Measure authorized live costs and verify the event setup before public release.

Contract references checked October 19, 2026:
[product API](https://elim.asia/en/docs/product/),
[API-key authentication](https://elim.asia/en/docs/auth/),
[pricing](https://elim.asia/en/pricing/),
[Apify event billing](https://docs.apify.com/sdk/python/docs/concepts/pay-per-event).
The provider's public trial-quota numbers differ between its product FAQ and
pricing page; confirm the account's actual quota rather than assuming either.

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
