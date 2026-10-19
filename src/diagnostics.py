"""Small failure reports without page source, credentials or challenge tokens."""

from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .parser import CARD, KEYWORD, text


def failure_report(html, url, stage, error, http_status=None):
    soup = BeautifulSoup(html or "", "html.parser")
    parts = urlsplit(url or "")
    challenge = "_____tmd_____" in parts.path.lower() or "/punish" in parts.path.lower()
    return {
        "stage": stage,
        "error_type": type(error).__name__,
        "error_code": getattr(error, "code", "collection_error"),
        "http_status": http_status,
        "http_status_source": "initial_page_navigation",
        "page_title": text(soup.title)[:160] or None,
        "url_host": parts.hostname,
        "url_query_present": bool(parts.query),
        "verification_url": challenge,
        "result_card_count": len(soup.select(CARD)),
        "keyword_input_present": bool(soup.select_one(KEYWORD)),
        "detail_title_present": bool(soup.select_one("#productTitle h1")),
        "data_handling": "No HTML, cookies, full URLs, request headers or challenge tokens are included.",
    }


async def capture_failure(page, spec, stage, error, callback, http_status=None):
    if callback is None:
        return
    try:
        html = await page.content()
        report = failure_report(html, page.url, stage, error, http_status)
    except Exception:
        report = {"stage": stage, "error_type": type(error).__name__,
                  "error_code": getattr(error, "code", "collection_error"), "page_unavailable": True}
    report.update(input_index=spec["index"], search_mode=spec["kind"])
    key = f"FAILURE_{spec['index']:02d}.json"
    try:
        await callback(key, report)
        error.diagnostic_key = key
    except Exception:
        # Diagnostic storage failure must never replace the actual collection error.
        error.diagnostic_storage_failed = True
    error.stage = stage
