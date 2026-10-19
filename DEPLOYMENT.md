# Private build and release checklist

## Repository and source

Use `https://github.com/jiazg23/1688-Scaper`, default branch `main`, source
directory `.`. `.actor/actor.json` points to the root Dockerfile. No API token,
saved browser session or personal credentials belong in this repository.

## Build privately first

1. Connect the repository to a private Apify development Actor.
2. Confirm the source build sees INPUT_SCHEMA, DATASET_SCHEMA and OUTPUT_SCHEMA.
3. Confirm `python -m src.main --check` passes during the Docker build.
4. Check proxy access explicitly. A new browser session is used; your Chrome
   sign-in, language and currency selections are not inherited.
5. Search/filter on 1688, copy the new results tab's address, choose Search results
   links and paste it into Links to 1688 search results. Start with one link,
   one page and five products. Inspect dataset, currency,
   MOQ, supplier links and the run summary before increasing limits.

## Evidence still needed

- A product-detail example with real quantity-price tiers, if available. The
  supplied public detail page is now parsed, but contains variant prices rather
  than volume tiers. Full details remain login-gated.
- Live validation of new-tab collection. The owner confirmed keyword results
  open a new tab, and ordinary tab handling passes offline tests.
- The surrounding real X/close-control markup for `iframe#alibaba-login-box`.
  Optional-popup closure is tested with synthetic wrappers, not the live popup.
- A second-page card capture and the final-page disabled Next state.
- An image-results page with its actual pagination markup.
- Permitted live search-link, keyword, multi-page, image and multi-image runs.

The development environment's browser policy currently blocks 1688. Do not
retry access through alternative domains, proxies, private APIs or other browser
surfaces to circumvent that policy. Saved-page work can continue offline.

## Before public release

- All live acceptance cases in VALIDATION.md must pass on the actual Apify build.
- Check build startup under Apify's normal limited permissions.
- Measure compute/proxy use, time, results and failure rate for multiple runs;
  only then decide pricing. No public price or billing event has been configured.
- Retest default input. Do not remove preview warnings until evidence supports it.
- Review terms, permissions and data handling for the intended users.
- Explicitly choose publication, monetization, platform timeouts and cost caps.

## Candidate display information

Name: **1688 Wholesale Product & Supplier Finder**

Current preview description:

> Development preview for 1688 product sourcing. Collect product and supplier
> listings from search-results links, keywords or images, with displayed prices, currencies,
> MOQs and CSV exports. Live collection has not yet passed release validation.

Do not advertise verified factories, exact order costs, automatic translation,
unlimited access or supported image search in a public listing before these
capabilities have actually been verified.
