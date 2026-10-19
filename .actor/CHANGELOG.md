# Changelog

## 0.1.2 — development preview, 2026-10-19

- Add Search results links mode: copy the new 1688 results tab's address and
  collect product cards with its filters, sorting and starting page retained.
- Remove individual product URL mode, productUrls input and its example. Retain
  the saved-detail parser only as an offline developer regression tool.
- Simplify input labels and expose separate product/page limits for search links.
- Start keyword/image searches at https://www.1688.com/ and follow ordinary
  new results tabs. Close optional login UI only through its own normal control.
- Full-page sign-in and real verification remain terminal. The owner's reported
  homepage redirect is not proven resolved; live release validation is pending.
- Expand the offline regression suite to 75 tests.

## 0.1.1 — development preview, 2026-10-19

- Fix false access-block detections caused by SDK challenge-path references
  and hidden login controls. Visible verification/login walls remain terminal.
- Add progress-stage logs and FAILURE_NN.json reports with specific detection
  codes and run-summary links; omit full URLs, cookies, source and challenge tokens.
- Extend offline suite to 59 tests. Owner's reported access failure still needs
  new diagnostic evidence; no live access fix is claimed.

## 0.1.0 — development preview, 2026-10-19

- Independent Python/Playwright Actor package and explicit module startup.
- Real supplied global-search card parser, selected-page currency evidence and
  Next-button pagination with product-change verification.
- Separate per-keyword/image limits, cross-input product deduplication,
  supplier shortlist exports and page-level recovery snapshots.
- Conservative pricing: no bulk quotation inferred from teaser prices.
- Offline regression suite and Linux/Docker CI checks.
- Real public detail DOM adapter for visible price, mixed-batch MOQ, color
  variants/stock, 38 captured attributes, gallery and aggregate product rating.
- Detail and search price currencies remain separate; login-gated data is flagged.
- Live access and direct product-detail acceptance remain incomplete.
