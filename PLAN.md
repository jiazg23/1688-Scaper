# 1688 Product & Supplier Finder — execution plan

## Goal

Build an independent Apify Actor for 1688 sourcing. The first release accepts
product URLs/offer IDs and keyword searches, extracts product and supplier data,
and reports the applicable published price tier for the buyer's order quantity.

## 1. Verify access and real data — saved search data verified; live access blocked

- Inspect live product and search responses, pagination and public structured data.
- Identify login/challenge responses separately from genuine empty results.
- Prove extraction on real pages before claiming production readiness.
- Do not call paid competitor Actors or fabricate missing product fields.

## 2. Implement the collection and sourcing logic — preview implemented

- Normalize supported 1688 offer URLs/IDs and search inputs.
- Implement a target-specific collector, bounded retries and optional Apify Proxy.
- Extract source-backed product IDs, titles, URLs, images, observed currencies, MOQ,
  quantity-price tiers and available supplier information.
- Select the price tier for the requested quantity; identify orders below MOQ
  and ambiguous variant-based prices without inventing a quotation.
- Deduplicate product results and provide a separate supplier shortlist export.
- Preserve completed work and report incomplete inputs in run summaries.

## 3. Package for Apify — complete locally

- Create the Actor, input, dataset and output schemas, requirements and Dockerfile.
- Keep the important input controls visible, with clear URL and keyword examples.
- Default named CSV exports on; offer combined products and supplier files.
- Keep price calculations explicit: product subtotal only, excluding freight/tax.
- Image controls are now implemented from supplied selectors and explicitly
  labelled preview/unverified; do not advertise them as a verified public feature.

## 4. Verify behavior — offline tests pass; live/container acceptance pending

- Test URL validation, tier boundaries, MOQ, missing/variant prices and deduplication.
- Test pagination, block/login detection, partial failures and export consistency.
- Run real-data smoke checks; distinguish them from fixture-based tests.
- Verify the Docker startup path and schema compatibility.

## 5. Prepare the launch — documentation complete; publication gated

- Write an accessible README with restrained emojis, examples and API/MCP guidance.
- Prepare display name, description, changelog and deployment instructions.
- Upload to the owner's explicitly selected `jiazg23/1688-Scaper` repository.
- Configure/build a private Apify Actor when a usable collection method is verified.
- Recommend pricing only after measuring collection cost; public publication and
  monetization require a reliable live build and an explicit final launch decision.

## Release acceptance

- Product URL mode returns real source-backed records.
- Keyword mode returns relevant records and actually follows pagination.
- Requested-quantity prices agree with source tiers and do not conceal MOQ limits.
- Invalid or blocked inputs do not masquerade as successful product collection.
- Tests, schemas and container startup pass; all unverified limits are documented.

## Progress notes

- 2026-10-19: Plan created. Existing sourcing Actors can supply layout/export
  conventions; the 1688 data collector must be implemented independently.
- 2026-10-19: No 1688 repository exists among the connected GitHub repositories.
- 2026-10-19: The web research fetcher could not open 1688 pages. Checking direct
  requests and a browser before selecting the implementation.
- 2026-10-19: Initial direct requests received verification/challenge HTML for
  both a product and keyword search, rather than product data. The browser's
  site-safety policy rejected the challenge destination. No CAPTCHA was solved
  and no alternative route was used to circumvent that rejection.
- 2026-10-19: Owner supplied real search/upload controls, 60 product cards,
  Next-button pagination and selected USD header/dropdown text. All 60 cards
  parse offline; USD is source-backed rather than assumed from a dollar symbol.
- 2026-10-19: Independent collector, input/output/dataset schemas, Dockerfile,
  CSV exports, per-input quotas, recovery summaries and offline CLI implemented.
- 2026-10-19: Five local-only Chromium control tests pass with all outgoing
  requests aborted. Initial process-sandbox launch failure was resolved with
  permission for these offline tests; it was not a 1688-access test.
- 2026-10-19: Local Docker daemon is unavailable; Docker checks are in CI.
- 2026-10-19: Owner selected public repository `jiazg23/1688-Scaper`; it is empty.
- 2026-10-19: Complete local suite passed: 38 tests, including five offline
  browser tests. Apify startup imports and installed dependency checks pass.
- 2026-10-19: Uploaded the full package to `jiazg23/1688-Scaper/main`. GitHub
  Actions passed Linux tests, Docker build and offline container/browser startup.
- 2026-10-19: Checked all four Actor definitions against Apify's published
  meta-schemas and removed an unsupported output-schema root keyword.
- 2026-10-19: Owner supplied a real public product-detail page. Added a strict,
  identity-matched DOM adapter for visible price, MOQ, variants/stock, attributes,
  gallery, supplier link and aggregate product rating. Full details are login-gated.
- 2026-10-19: Detail page price symbol is ¥, not the USD card price. Preserve
  context; do not infer quantity tiers from color variants or unknown currency.
- 2026-10-19: Expanded suite passed all 45 tests. All four Actor definition files
  pass Apify's published meta-schemas after adding detail fields.
- Remaining source requirement: actual quantity-tier examples if bulk quotes are
  desired, image-results pagination and confirmed search-tab behavior. Live access,
  fresh-session currency/language, deployment and pricing remain unvalidated.
