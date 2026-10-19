# 1688 Wholesale Product & Supplier Finder

Collect source-backed product and supplier information from **keywords** or
**numeric Offer IDs**, then download a product CSV and supplier shortlist.

> **Development preview — live access is not release-validated.** Earlier owner
> runs encountered full-page login and verification responses. The latest HK
> run reached the homepage but failed at keyword entry. No successful live
> product collection is established by the offline tests or container startup.

## 🔎 Two ways to start

| Input | What happens |
| --- | --- |
| **Search keywords (English or Chinese)** | Search each product name, extract supported result-card fields and follow Next page until a limit or the last page. |
| **Offer IDs** | Open each requested product's public detail page and extract supported visible fields. |

**Offer IDs take priority.** If any IDs are filled, keywords are ignored,
including the prefilled example. There is no search-mode dropdown.
Image search, uploaded photos, search-results links and full product URL inputs
have been removed.

For a product at `detail.1688.com/offer/1071313125369.html`, enter only
`1071313125369` in **Offer IDs**. This is an example from the owner's saved
HTML, not a guarantee of current product availability.

This collector is independent. It does not call Zen Studio, another paid
Actor, or an external product-data service. Its form follows familiar input
conventions; its private competitors' collection code has not been reproduced.

## What you get

Keyword results include product ID, title, product/image links, displayed price,
observed currency, MOQ, supplier name/storefront and visible seller metadata.
Repeated products appear once, retaining every keyword that matched.

Offer ID results can additionally include the source's visible variant prices
and stock, product attributes, gallery images and product-review rating.
Login-gated completeness is flagged; hidden data is not invented.

The supplier CSV groups products by storefront or supplier ID, not company
name alone. It does not create additional supplier records in the product dataset.

Unavailable values are `null`. Unlabelled badge images do not establish factory
or verified-supplier status. Product attributes are seller claims, not independently
verified certifications. Keyword search does **not** automatically enrich every
result from its detail page.

### Prices, currency and MOQ

- Currency comes from explicit page settings or source evidence. A dollar or
  yuan/yen symbol alone does not establish an ISO currency.
- The saved search page is explicitly USD; its detail-page capture displays
  `¥25.00` without an ISO currency setting. These are distinct price contexts.
- `orderQuantity` checks the displayed MOQ. Listing and variant prices are
  **not confirmed bulk quotations**.
- The captured color variants are not quantity-discount tiers. Real quantity-tier
  extraction and order-subtotal calculation are not connected.
- Stock is a displayed snapshot, not an inventory guarantee.

English keywords are accepted; titles are returned as displayed. No automatic
translation, currency conversion, sorting filters or paid Supplier Intelligence
add-on is included.

## 🚀 Quick start on Apify

1. Connect this repository to a **private development Actor**, branch `main`,
   source directory `.`, using `.actor/actor.json`.
2. Build the latest source. Check your residential proxy access and country
   availability in **Apify Console → Proxy**.
3. Enter one keyword, or clear the example and enter numeric Offer IDs.
4. For an initial test, set **Maximum products per keyword** to 5 and
   **Maximum pages per keyword** to 1. Choose appropriate native Apify timeout
   and spending limits before starting.
5. Inspect the dataset and `RUN_SUMMARY.json`. Download CSVs from
   **Storage → Key-value store**.

Keyword example:

```json
{
  "keywords": ["wireless earbuds"],
  "offerIds": [],
  "maxResults": 5,
  "maxPagesPerKeyword": 1,
  "useApifyProxy": true,
  "proxyCountryMode": "CN",
  "saveCsvFile": true
}
```

Known-product example:

```json
{
  "keywords": [],
  "offerIds": ["1071313125369"],
  "useApifyProxy": true,
  "proxyCountryMode": "CN",
  "saveCsvFile": true
}
```

Each keyword has its own product/page budget. Defaults are **100 products**
and **5 pages** per keyword. The 10,000-product setting is a hard ceiling,
**not unlimited** and not a promise of that many results. Offer IDs are processed
individually and ignore keyword/page limits. Limits: 20 keywords or 100 IDs per run.

## Residential proxies and costs

When enabled, the Actor explicitly requests Apify's **RESIDENTIAL** group.
**China (CN)** is the default; **Hong Kong (HK)** is an alternative selected
before the run. The selected country must be available to the account.

One proxy session is configured before browsing. There is no automatic
country/identity switching after login, verification or denial, and no silent
fallback to a direct connection if proxy initialization fails.

Residential traffic is billed through Apify by data transferred, including
traffic spent on failed attempts. No third-party proxy purchase is made by this
repository. Credentials come from the Apify SDK and are not logged or committed.
See [residential proxy documentation](https://docs.apify.com/proxy/residential-proxy).

Your own tests use your prepaid platform usage. For public pay-per-event Actors,
usage can be included in your result price or billed separately according to
your monetization settings. This repository does not change pricing, purchase
access or configure Store billing. Measure costs before setting event prices:
[Apify monetization](https://docs.apify.com/actors/publishing/monetize).

The native Apify **Timeout**, **Memory** and **Maximum cost per run** remain in
Run options. No unlimited processing-time or spending default is imposed here.

## 📁 Exports and recovery

- `1688_products.csv` — product CSV, enabled by default; filename is configurable.
- `1688_suppliers.csv` — supplier shortlist derived from those products.
- `RUN_SUMMARY.json` — per-input counts, outcomes, limits and errors.
- `PARTIAL_RESULTS.json` — last saved page-level products; recovery snapshot,
  not automatic resume.
- `FAILURE_01.json` and subsequent numbers — failure stage/reason, page title,
  final host and card/control counts. No raw HTML, credentials, full URLs or
  challenge query tokens are copied to this report.

Since 0.2.1, keyword-entry/submission failures also include `search_controls`
and `search_buttons`: bounded IDs/classes, public control attributes, visibility,
read-only state and open-shadow-root metadata. **Form values are not collected.**
`keyword_control_unavailable` identifies a missing/unusable known search box;
it is distinct from a login redirect. Send this report when a regional homepage
does not match the supplied global-page controls. Unknown controls are reported,
not clicked speculatively.

Products are written once per product to the dataset when collection ends.
A hard platform timeout may interrupt final dataset/CSV writes; check the
page-level recovery snapshot. CSV cells are protected against formula injection.

## Access failures

The Actor uses an isolated browser, not your signed-in Chrome session. It does
not import cookies, solve CAPTCHAs, remove authentication walls, call guessed
private APIs or rotate identities after denial.

An optional login popup can be closed through its own visible control only when
usable public content remains behind it. A full-page login redirect or genuine
verification screen stops the batch and preserves earlier collected products.

The owner's subsequent HK run reached the public homepage (HTTP 200, title
`阿里1688首页`) and then timed out at keyword entry, with no known global-page
input in the captured main HTML. A regional layout difference, an unready
component or shadow/hidden control needs actual control evidence to distinguish.
The collector now selects a usable known control rather than its first DOM match.

**The live collection failures are not proven fixed.** The HK run establishes
homepage access for that session, not working product search. Version 0.2.1's
control-selection and diagnostic changes have only been tested offline.
Unknown layouts fail explicitly rather than pretending to be successful
zero-result searches. Use only authorized data and respect applicable site terms.

## API and MCP

Deploy privately and use your actual Actor ID with the
[Apify API](https://docs.apify.com/api/v2/acts-runs-post) or a connected
[Apify MCP server](https://docs.apify.com/platform/integrations/mcp).
Send the same JSON as the form. No deployed Actor ID or API token is bundled.

For older keyword clients, `searchTerms`, `maxProductsPerKeyword` and
`maxPagesText` remain supported aliases when their new fields are absent.
Old image/search-link inputs fail explicitly; they do not silently run the example.
`proxyCountryMode: "rotate"` and unimplemented enrichment/filter options are
not interchangeable with another creator's Actor.

## Local development

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium --only-shell
.venv/bin/python -m src.main --check
.venv/bin/python -m unittest discover -s tests -v
```

Parse saved HTML without accessing 1688 or executing captured scripts:

```sh
.venv/bin/python -m src.offline saved-results.html --header selected-currency.html --format json
.venv/bin/python -m src.offline saved-detail.html --product-url 1071313125369 --format json
```

Use header evidence from the same captured page/session. CI checks saved-page
parsing, keyword and Offer ID workflows, proxy configuration mocks, pagination,
recovery, schemas and offline Docker/Chromium startup. It makes no live 1688
requests or paid proxy calls.

See [validation status](VALIDATION.md) and [deployment checklist](DEPLOYMENT.md).
