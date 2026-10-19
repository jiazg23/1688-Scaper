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
- `login-iframe.html` retains the owner's supplied `alibaba-login-box` iframe ID
  and login endpoint. Session, tracking and redirect query parameters are removed.
  Surrounding close buttons, popup events and new-tab result content in browser
  tests are synthetic; the actual surrounding X markup has not been supplied.
- `product-detail.html` is reduced from the owner's product-detail HTML supplied
  later the same day for offer 1071313125369. Visible title, main price, two
  color variants, stock metadata, MOQ promotion, attributes and supplier links
  are retained. Only aggregate product rating is retained, not buyer identities,
  avatars or review text. Tracking query parameters, SVGs and shadow templates
  are removed. Offer ID query evidence is preserved for identity matching.
- Product-detail JSON-LD and quantity tiers in tests are synthetic schema
  examples. The real supplied detail page shows variant prices, not quantity tiers.

No saved session, cookies, account credentials, CAPTCHA tokens or HAR traffic
are included. Tests execute locally with all network requests blocked.
