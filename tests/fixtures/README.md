# Fixture provenance

- `search-controls.html` and `search-results.html` come from the owner's saved
  1688 global-page HTML supplied on October 19, 2026. All 60 product wrappers
  are retained. SVGs, scripts, tracking tokens and unrelated attributes were
  mechanically removed. The ad flag is reduced to `_p_isad@1` only.
- `currency-usd.html` preserves the selected `Other-English-USD` header and
  `USD ($)` dropdown text supplied by the owner.
- `pagination.html` preserves the class names, state and labels of the supplied
  page-1 pagination fragment; irrelevant styling and tracking were removed.
- Browser test event handlers are **synthetic**. They prove the collector can
  operate these controls and detect changed cards, not that live 1688 permits it.
- Product-detail JSON-LD and price tiers used by tests are synthetic schema
  examples. No real detail-page/quantity-tier fixture has been supplied yet.

No saved session, cookies, account credentials, CAPTCHA tokens or HAR traffic
are included. Tests execute locally with all network requests blocked.
