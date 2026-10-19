"""Small failure reports without page source, credentials or challenge tokens."""

from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .parser import CARD, KEYWORD, text


async def search_control_report(page):
    """Read only bounded UI metadata, including open shadow roots. Never values."""
    return await page.locator("input, textarea, button, [role='searchbox'], [role='button']").evaluate_all(
        """(nodes, knownSelector) => {
            const attr = (n, key) => (n.getAttribute(key) || '').slice(0, 160);
            const visible = n => {
                const s = getComputedStyle(n), r = n.getBoundingClientRect();
                return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
            };
            const fields = nodes.filter(n =>
                n.tagName === 'TEXTAREA' || n.getAttribute('role') === 'searchbox' ||
                (n.tagName === 'INPUT' && ['text', 'search'].includes(n.type)));
            const buttons = nodes.filter(n => {
                if (!(n.tagName === 'BUTTON' || n.getAttribute('role') === 'button' ||
                      (n.tagName === 'INPUT' && n.type === 'submit'))) return false;
                const label = n.getAttribute('aria-label') || (n.tagName === 'INPUT' ? '' : n.textContent) || '';
                return /search|搜索|搜货|找货|搜一下/i.test(label) || n.getAttribute('data-tracker') === 'textSearch.search';
            });
            const describe = n => ({
                tag: n.tagName.toLowerCase(), type: attr(n, 'type'), id: attr(n, 'id'),
                name: attr(n, 'name'), class: attr(n, 'class'), role: attr(n, 'role'),
                placeholder: attr(n, 'placeholder'), aria_label: attr(n, 'aria-label'),
                tracker: attr(n, 'data-tracker'), visible: visible(n), disabled: !!n.disabled,
                readonly: !!n.readOnly, open_shadow_root: n.getRootNode() instanceof ShadowRoot,
                known_keyword_match: n.matches(knownSelector)
            });
            return {
                search_controls: fields.slice(0, 20).map(describe),
                search_buttons: buttons.slice(0, 20).map(describe),
                search_control_count: fields.length, search_button_count: buttons.length,
                search_controls_truncated: fields.length > 20 || buttons.length > 20
            };
        }""", KEYWORD)


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
        "data_handling": "No raw HTML, form values, cookies, full URLs, request headers or challenge tokens are included. Search failures may include bounded control attributes, visibility and editability metadata.",
    }


async def capture_failure(page, spec, stage, error, callback, http_status=None):
    if callback is None:
        return
    try:
        html = await page.content()
        report = failure_report(html, page.url, stage, error, http_status)
        if stage in {"entering_keyword", "submitting_keyword"}:
            try:
                report.update(await search_control_report(page))
            except Exception:
                report["search_controls_unavailable"] = True
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
