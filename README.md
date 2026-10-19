# 1688 Wholesale Product & Supplier Finder

Build a sourcing shortlist from 1688 product listings: product links, displayed
prices, MOQ, supplier storefronts and the searches that matched each product.

> **Development preview — not ready for public release.** The parser is tested
> against 60 real saved product cards and a real public product-detail page
> supplied by the owner. Live search,
> uploads, regional page behavior and direct product-detail extraction have
> not passed acceptance tests. See [validation status](VALIDATION.md).

## 🔎 Search your way

- **Keyword product search:** enter product names, with separate product/page
  limits for every keyword.
- **Image product search:** upload a product image or supply a direct HTTPS
  PNG/JPEG/WebP URL. Each image is searched separately. The upload controls are
  implemented from supplied HTML; live image results still need verification.
- **Direct product URLs:** provide 1688 offer URLs or IDs. Extract the visible
  detail price, variants and stock, gallery images, product attributes, product
  rating and supplier link from the captured public detail-page layout. Mark
  login-gated details as partial. Product JSON-LD is an additional fallback.

This is an independent collector. It does **not** call a competitor's paid
Actor or wrap the Alibaba/Made-in-China Actors.

## What the output contains

| Product information | Supplier information | Sourcing context |
| --- | --- | --- |
| Offer ID, title, canonical URL, image | Supplier ID, name, storefront | Every matching keyword/image |
| Displayed price and observed currency | Visible seller tenure and rating | Displayed MOQ and requested quantity |
| Marketing labels and displayed sales text | Separate supplier shortlist CSV | Price/quote status and collection timestamp |

Unavailable values are `null`, not invented. Hidden ratings are not exported as
visible ratings. Unlabelled badge images do not establish verification or
manufacturer status. Sales text such as `9K+ sold` is preserved, not converted
into a falsely exact sales count.

### Currency and pricing you can interpret

The owner's supplied page is explicitly **USD**, confirmed by its
`Other-English-USD` header and `USD ($)` selector. The parser reads those
selected settings. A `$` symbol alone is not enough to assume USD.

The supplied detail page is a different pricing context: it displays `¥25.00`,
two color variants at `¥25`, and a two-piece mixed-batch minimum. Its fragment
does not include an explicit ISO currency setting, so `price_symbol` is `¥` and
`currency` remains `null`. The USD search-card price is not copied over it.

Each fresh run reports the currency actually observed on its pages. The Actor
does not import your Chrome settings, force USD, translate titles, or convert
currencies. Never combine USD and CNY prices as if they were the same currency.

`orderQuantity` currently checks the displayed MOQ. A search-card price can
depend on variants, promotions or quantity; it is **not** a confirmed bulk quote.
Search cards therefore return `quote_status: "listing_price_only"` and no
calculated subtotal. The decimal tier calculator is unit-tested, but real
quantity-tier extraction is not connected: the supplied detail rows describe
colors and stock, not volume discounts. Detail records with those rows return
`variant_selection_required`. Stock is a displayed snapshot, not a guarantee.
Any future tier subtotal excludes freight, taxes, duties and service fees.

## Quick start on Apify

1. Create a **private development Actor** from this GitHub repository, branch
   `main`, using the root directory and `.actor/actor.json`.
2. Build it, select **Keyword product search**, and start with one query and
   a small limit. Do not publish or monetize before completing [acceptance](VALIDATION.md).
3. Inspect the dataset **and** `RUN_SUMMARY.json`. A successful run can retain
   partial results when a later input fails.
4. Download the named CSVs from the run's **Storage → Key-value store**.

```json
{
  "searchMode": "keyword",
  "searchTerms": ["hair dryer"],
  "maxProductsPerKeyword": 50,
  "maxPagesText": 5,
  "orderQuantity": 100,
  "useApifyProxy": true,
  "saveCsvFile": true
}
```

For image search, choose `"searchMode": "image"` and fill `uploadedImages` or
`imageUrls`. Use **an image file URL**, not a search page, a product page, a
temporary `blob:` URL, or a Markdown link. Limit: 20 images per run, 10 MB each.
The website receives the images you explicitly supply for that search.

For direct products, choose `"searchMode": "urls"` and populate `productUrls`
with `https://detail.1688.com/offer/1071313125369.html` or an offer ID. This URL
is an example from the owner's saved listing, not a guarantee of current availability.
Direct URL mode reads the public detail page; keyword/image mode exports search
cards and does not automatically visit every result for detail enrichment.

### Clear limits, no duplicate timeout controls

The product target is **per keyword or image**, not a global first-image cutoff.
Products repeated across inputs appear once in the dataset, with all matched
inputs retained. The supplier CSV groups by storefront/ID, not company name alone.

Native Apify **Timeout**, **Memory**, and **Maximum cost per run** remain in
Apify's Run options. This repository neither hides nor overrides your cost cap.
No unlimited timeout or unlimited spending default is imposed by the code.
Apify Proxy defaults on and requires access; it does not guarantee site access.

## 📁 Exports and recovery

- `1688_products.csv` — products, enabled by default; filename is configurable.
- `1688_suppliers.csv` — supplier shortlist grouped from collected products.
- `RUN_SUMMARY.json` — per-input status, pages, counts, errors and stop reasons.
- `PARTIAL_RESULTS.json` — last saved page-level products, even before the final
  dataset write. This is a recovery snapshot, not automatic resume.
- `FAILURE_01.json` (and subsequent input numbers) — stage, detection reason,
  page title/host and card/control counts when a search fails. Full URLs, page
  HTML, cookies, passwords and challenge tokens are not copied to this report.

Dataset records are written once per product when collection ends. A hard
platform timeout may interrupt the final dataset/CSV write; check the recovery
snapshot. Supplier exports do not add extra supplier rows to the product dataset.
CSV cells are protected against spreadsheet formula injection.

## Access restrictions and honest failures

The browser uses a new isolated session, not your signed-in browser. There is
no cookie import, fingerprint evasion, CAPTCHA solver or proxy rotation. When
1688 denies access or requests verification, the batch stops and preserves
already-collected products. Unknown layouts are reported as errors, not as
successful zero-result searches.

Search controls and pagination come from the supplied global-page HTML. Other
regional layouts, new-tab search behavior and image-result pagination still
need live validation. The collector does not guess private endpoints to work
around missing controls. Use only data and images you are authorized to process,
and respect the site's terms and applicable requirements.

### If the run says “verification”

The first owner-reported keyword run reached browser startup but failed in the
old access detector. That detector could falsely flag ordinary script references
or hidden login UI. Version `0.1.1` fixes those reproducible cases and records
the precise stage/reason; it does **not** bypass a genuine verification page.

Rebuild from the latest `main` and inspect `FAILURE_01.json` plus
`RUN_SUMMARY.json` if the same input still fails. `opening_homepage` versus
`submitting_keyword`/`waiting_for_results` identifies where it stopped.
`http_status` refers to the initial page navigation, not every later request;
an HTTP 200 response can still display a verification page. Raising the Actor's
overall processing-time limit does not resolve an active access challenge.

## API and MCP usage

After deploying your private Actor, use its actual Actor ID with the
[Apify API](https://docs.apify.com/api/v2/acts-runs-post), sending the same JSON
as the input form. Keep the API token in an environment variable, not a URL or
committed file. There is no deployed Actor ID bundled in this repository.

With a connected [Apify MCP server](https://docs.apify.com/platform/integrations/mcp),
select your deployed Actor and provide its input fields. Instruct the assistant
to inspect `RUN_SUMMARY.json`, report partial results, retain currency, and avoid
describing search-card prices as confirmed order quotations.

## Local development and offline parsing

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium --only-shell
.venv/bin/python -m src.main --check
.venv/bin/python -m unittest discover -s tests -v
```

Parse a saved results page without connecting to 1688 or executing saved scripts:

```sh
.venv/bin/python -m src.offline saved-results.html --header selected-currency.html --format json
.venv/bin/python -m src.offline saved-results.html --header selected-currency.html --format csv
.venv/bin/python -m src.offline saved-detail.html --product-url 1071313125369 --format json
```

The offline command writes to standard output. The optional header file must
contain the currency setting from the **same captured page/session**.

The CI workflow tests validation, pricing, export safety, per-input limits,
partial failures, saved-card parsing, offline browser controls and Docker startup.
It does not make live 1688 requests. See [the plan](PLAN.md),
[validation details](VALIDATION.md), and [deployment checklist](DEPLOYMENT.md).
