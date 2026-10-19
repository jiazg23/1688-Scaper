# 1688 Wholesale Product & Supplier Finder

Build a sourcing shortlist from 1688 product listings: product links, displayed
prices, MOQ, supplier storefronts and the searches that matched each product.

> **Development preview — not ready for public release.** The parser is tested
> against 60 real saved product cards supplied by the owner. Live search,
> uploads and regional page behavior have not passed acceptance tests.
> See [validation status](VALIDATION.md).

## 🔎 Search your way

- **Search results links:** search and apply filters on 1688 yourself, then copy
  the address from the new tab showing the results. Paste it into the Actor to
  collect those product cards. Your link's filters, sorting and starting page
  are retained.
- **Keyword product search:** enter product names, with separate product/page
  limits for every keyword.
- **Image product search:** upload a product image or supply a direct HTTPS
  PNG/JPEG/WebP URL. Each image is searched separately. The upload controls are
  implemented from supplied HTML; live image results still need verification.

All three modes collect **search-result product cards**. Individual product
URLs and offer IDs are not supported Actor inputs.

This is an independent collector. It does **not** call a competitor's paid
Actor or wrap the Alibaba/Made-in-China Actors.

## What the output contains

| Product information | Supplier information | Sourcing context |
| --- | --- | --- |
| Offer ID, title, canonical URL, image | Supplier ID, name, storefront | Every matching search link, keyword or image |
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

Each fresh run reports the currency actually observed on its pages. The Actor
does not import your Chrome settings, force USD, translate titles, or convert
currencies. Never combine USD and CNY prices as if they were the same currency.

`orderQuantity` currently checks the displayed MOQ. A search-card price can
depend on variants, promotions or quantity; it is **not** a confirmed bulk quote.
Search cards therefore return `quote_status: "listing_price_only"` and no
calculated subtotal. Real quantity-tier extraction is not connected. Prices
exclude any separately charged freight, taxes, duties and service fees.

## Quick start on Apify

1. Create a **private development Actor** from this GitHub repository, branch
   `main`, using the root directory and `.actor/actor.json`.
2. On 1688, search for a product and select any filters you need. Copy the
   address from the **new tab showing the product results**.
3. Build the Actor, choose **Search results links — paste from 1688**, and paste
   that address into **Links to 1688 search results**. Start with one link,
   one page and five products. Do not publish or monetize before completing
   [acceptance](VALIDATION.md).
4. Inspect the dataset **and** `RUN_SUMMARY.json`. A successful run can retain
   partial results when a later input fails.
5. Download the named CSVs from the run's **Storage → Key-value store**.

```json
{
  "searchMode": "search_urls",
  "searchUrls": ["https://air.1688.com/kapp/1688-global/sales/search?keywords=hair%20dryer"],
  "maxProductsPerSearchUrl": 5,
  "maxPagesPerSearchUrl": 1,
  "orderQuantity": 100,
  "useApifyProxy": true,
  "saveCsvFile": true
}
```

Use the actual results address from your browser, not the homepage, a login
link, an iframe address, or a single product link. A copied link does **not**
transfer your browser login or cookies to Apify. The page limit counts from the
starting page in your link; the Actor does not intentionally restart on page 1.

For keyword search, choose `"searchMode": "keyword"` and enter `searchTerms`,
such as `["hair dryer"]`. Keyword and image search start at exactly
`https://www.1688.com/`; the collector follows a new results tab if one opens.

For image search, choose `"searchMode": "image"` and fill `uploadedImages` or
`imageUrls`. Use **an image file URL**, not a search page, a product page, a
temporary `blob:` URL, or a Markdown link. Limit: 20 images per run, 10 MB each.
The website receives the images you explicitly supply for that search.

### Clear limits, no duplicate timeout controls

The product target is **per search link, keyword or image**, not a global cutoff.
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

An optional login popup can be closed through its own visible X/close control
when public content is available behind it. A full-page login redirect or genuine
verification screen is not a dismissible popup and remains a terminal error.

Search controls and pagination come from the supplied global-page HTML. Other
regional layouts, new-tab collection and image-result pagination still need
live validation. New-tab and optional-popup handling are tested offline. The
collector does not guess private endpoints to work
around missing controls. Use only data and images you are authorized to process,
and respect the site's terms and applicable requirements.

### If the run says “verification”

The initial detector could falsely flag ordinary script references or hidden
login UI; version `0.1.1` fixed those reproducible cases. The subsequent owner
failure report records a full-page `login.taobao.com` redirect at
`opening_homepage`, before a keyword was submitted. Version `0.1.2` adds normal
optional-popup dismissal and new-tab handling, but does **not** bypass that
full-page redirect or establish that live access is fixed.

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
The saved-detail command is a developer-only parser regression tool; it does
not expose individual product URL mode in the Actor.

The CI workflow tests validation, pricing, export safety, per-input limits,
partial failures, saved-card parsing, offline browser controls and Docker startup.
It does not make live 1688 requests. See [the plan](PLAN.md),
[validation details](VALIDATION.md), and [deployment checklist](DEPLOYMENT.md).
