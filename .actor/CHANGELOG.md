# Changelog

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
