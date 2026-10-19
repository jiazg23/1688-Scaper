"""Parsers for user-supplied global search DOM and conservative JSON-LD fallback.

No execution of embedded scripts. No guessed private API response adapters.
"""

import json
import re
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from .config import product_url, InputError
from .pricing import decimal_text

CARD = ".cgf-sale-product-list-card-wrapper[data-offerid]"
NEXT = ".cgf-sale-pagination-next"
KEYWORD = "textarea.cgf-search-input__input"
SEARCH = 'button[data-tracker="textSearch.search"]'


class CollectionError(RuntimeError):
    pass


class AccessBlocked(CollectionError):
    def __init__(self, message, code="access_blocked"):
        super().__init__(message)
        self.code = code


class UnsupportedLayout(CollectionError):
    pass


def check_http_status(status):
    if status in {401, 403, 429}:
        code = "http_rate_limit" if status == 429 else "http_access_denied"
        raise AccessBlocked(f"1688 returned HTTP {status}; collection stopped without retrying another identity.", code)


def text(node):
    return node.get_text(" ", strip=True) if node else ""


def hidden(node):
    while node:
        style = re.sub(r"\s+", "", node.get("style", "")).lower()
        if node.has_attr("hidden") or node.get("aria-hidden") == "true" or "display:none" in style or "visibility:hidden" in style:
            return True
        node = node.parent if getattr(node.parent, "attrs", None) is not None else None
    return False


def check_access(html, url="", visible_signals=None):
    soup = BeautifulSoup(html, "html.parser")
    title = text(soup.title).lower()
    parts = urlsplit(url)
    if "_____tmd_____" in parts.path.lower() or re.search(r"(?:^|/)punish(?:/|$)", parts.path, re.I):
        raise AccessBlocked("1688 opened a verification URL. No verification bypass was attempted.", "verification_url")
    if any(marker in title for marker in ("captcha", "access denied", "安全验证", "访问受限")):
        raise AccessBlocked("1688 displayed a verification/access-denied page title.", "verification_title")
    challenge_nodes = soup.select('#nc_1_wrapper, #baxia-dialog-content, iframe[src*="punish"], iframe[src*="captcha"]')
    active_challenge = (visible_signals["verification_element"] if visible_signals is not None
                        else any(not hidden(n) for n in challenge_nodes))
    if active_challenge:
        raise AccessBlocked("1688 displayed a verification control or frame.", "verification_element")
    # A reference inside an SDK script is not navigation. Only an actual meta
    # refresh destination is evidence of a requested challenge redirect.
    for node in soup.select('meta[http-equiv]'):
        if node.get("http-equiv", "").lower() == "refresh":
            content = node.get("content", "").lower()
            if "_____tmd_____" in content or re.search(r"/punish(?:[/?'\";]|$)", content):
                raise AccessBlocked("1688 requested a verification-page redirect.", "verification_redirect")
    # Standalone challenge responses may consist only of a configuration script.
    # Do not flag a generic captcha configuration in an otherwise normal app.
    app = soup.select_one(CARD + ", " + KEYWORD + ", #productTitle h1")
    if app is None:
        decoder = json.JSONDecoder()
        for script in soup.select("script"):
            source = script.string or script.get_text()
            for match in re.finditer(r"(?:\b(?:var|let|const)\s+\w+|(?:window\.)?_config_)\s*=\s*(?=\{)", source):
                try:
                    config, _ = decoder.raw_decode(source[match.end():])
                except json.JSONDecodeError:
                    continue
                if isinstance(config, dict) and config.get("action") == "captcha":
                    raise AccessBlocked("1688 returned a standalone verification configuration.", "verification_config")
    host = parts.hostname or ""
    if host in {"login.1688.com", "login.taobao.com", "passport.1688.com"}:
        raise AccessBlocked("1688 opened a sign-in page; browser credentials are not imported.", "login_url")
    active_login = (visible_signals["login_form"] if visible_signals is not None
                    else any(not hidden(n) for n in soup.select('input[type=password]')))
    if active_login:
        raise AccessBlocked("1688 displayed a sign-in form; browser credentials are not imported.", "login_form")


def page_currency(soup):
    # The user supplied both header and dropdown evidence. Read selected values,
    # not the full dropdown options or an arbitrary '$' symbol.
    currencies = set()
    for node in soup.select(".oversea-language-text, .currency-section .select-value .select-text"):
        found = re.search(r"(?:^|[^A-Z])(USD|CNY|EUR|GBP|CAD|AUD|JPY|HKD)(?:$|[^A-Z])", text(node).upper())
        if found:
            currencies.add(found[1])
    return next(iter(currencies)) if len(currencies) == 1 else None


def supplier_url(value):
    try:
        p = urlsplit(value)
        if (p.scheme == "https" and p.hostname and p.hostname.endswith(".1688.com")
                and p.port in {None, 443} and not p.username and not p.password):
            return f"https://{p.hostname}"
    except (ValueError, TypeError, AttributeError):
        pass
    return None


def parse_search(html, url="", visible_signals=None):
    check_access(html, url, visible_signals)
    soup = BeautifulSoup(html, "html.parser")
    currency = page_currency(soup)
    products, ids = [], set()
    for card in soup.select(CARD):
        offer_id = card.get("data-offerid", "")
        title = text(card.select_one(".cgf-card-title"))
        if not re.fullmatch(r"[0-9]{6,20}", offer_id) or not title or offer_id in ids:
            continue
        ids.add(offer_id)
        price_node = card.select_one(".cgf-card-price")
        amount = "".join(text(price_node.select_one(selector)) if price_node else ""
                         for selector in (".cgf-integer", ".cgf-dot", ".cgf-decimal"))
        amount = decimal_text(amount.replace(",", ""))
        symbol = text(card.select_one(".cgf-card-price .cgf-unit")) or None
        explicit = {"US$": "USD", "USD": "USD", "CNY": "CNY", "RMB": "CNY", "€": "EUR", "£": "GBP"}.get(symbol)
        # Conflicting evidence must not silently relabel a price.
        actual_currency = explicit or currency
        if explicit and currency and explicit != currency:
            actual_currency = None
        if symbol in {"¥", "￥"} and currency not in {"CNY", "JPY"}:
            actual_currency = None
        if symbol == "$" and currency not in {"USD", "CAD", "AUD", "HKD"}:
            actual_currency = None
        moq_text = text(card.select_one(".cgf-card-moq"))
        match = re.fullmatch(r"(?:MOQ\s*[:：]?\s*|起订量\s*[:：]?\s*)([0-9][0-9,]*)(?:\s*(pcs|pieces?|units?|件|个))?", moq_text, re.I)
        moq = int(match[1].replace(",", "")) if match else None
        anchor = card.select_one(".cgf-card-shop-name a[href]")
        image = card.select_one(".cgf-card-image img.cgf-img")
        meta = [text(n) for n in card.select(".cgf-data-row .cgf-item") if not hidden(n)]
        years = next((re.fullmatch(r"(\d+)\s*(?:yrs?|years?|年)", m, re.I) for m in meta if re.fullmatch(r"(\d+)\s*(?:yrs?|years?|年)", m, re.I)), None)
        rating = card.select_one(".cgf-rating-score")
        score = decimal_text(text(rating)) if rating and not hidden(rating) else None
        report = card.get("data-aplus-report", "")
        products.append({
            "product_id": offer_id, "product_url": product_url(offer_id), "title": title,
            "image_url": image.get("src") if image else None,
            "display_price": amount, "currency": actual_currency, "price_symbol": symbol,
            "currency_source": "card" if explicit and actual_currency else "page_setting" if actual_currency else None,
            "moq": moq, "moq_text": moq_text or None,
            "quantity_unit": match[2] if match and match[2] else None,
            "price_basis": "search_card", "price_tiers": [],
            "supplier_id": card.get("data-supplierid") or None,
            "supplier_name": text(anchor) or None,
            "supplier_url": supplier_url(anchor.get("href", "")) if anchor else None,
            "supplier_years": int(years[1]) if years else None,
            "supplier_rating": float(score) if score is not None and 0 <= float(score) <= 5 else None,
            "sales_text": next((m for m in meta if re.search(r"sold|已售", m, re.I)), None),
            "marketing_tags": list(dict.fromkeys(text(t) for t in card.select(".cgf-card-marketing .cgf-tag") if text(t))),
            "is_sponsored": True if "_p_isad@1" in report else None,
            "verified_supplier": None, "manufacturer": None,
            "extraction_source": "1688_global_search_dom",
        })
    if not products:
        # Unknown/challenge layouts must not be called successful empty searches.
        raise UnsupportedLayout("No supported 1688 product cards found. Need a current results-page sample; this is not confirmed zero results.")
    next_node = soup.select_one(NEXT)
    active = text(soup.select_one(".cgf-sale-pagination-page-active"))
    has_next = (not next_node.has_attr("disabled") and next_node.get("aria-disabled") != "true") if next_node else None
    return {"products": products, "has_next": has_next, "page_number": int(active) if active.isdigit() else None}


def parse_product(html, url, visible_signals=None):
    """Captured 1688 detail DOM, then an identity-matched JSON-LD fallback."""
    check_access(html, url, visible_signals)
    expected_url = product_url(url)
    soup = BeautifulSoup(html, "html.parser")
    if soup.select_one("#productTitle h1"):
        return parse_detail_dom(soup, expected_url)
    def walk(value):
        if isinstance(value, list):
            for item in value:
                yield from walk(item)
        elif isinstance(value, dict):
            types = value.get("@type", [])
            if "Product" in (types if isinstance(types, list) else [types]):
                yield value
            yield from walk(value.get("@graph", []))
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            candidates = list(walk(json.loads(script.string or script.get_text())))
        except (json.JSONDecodeError, TypeError):
            continue
        for item in candidates:
            try:
                # Require identity evidence, not the first recommended Product.
                if product_url(item.get("url", "")) != expected_url:
                    continue
            except (InputError, AttributeError):
                continue
            if not isinstance(item.get("name"), str) or not item["name"].strip():
                continue
            offers = item.get("offers", {})
            offer = offers if isinstance(offers, dict) else {}
            currency = offer.get("priceCurrency")
            if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
                currency = None
            image = item.get("image")
            if isinstance(image, list):
                image = image[0] if image else None
            if isinstance(image, dict):
                image = image.get("url")
            seller = offer.get("seller", {})
            seller = seller if isinstance(seller, dict) else {}
            return {"product_id": expected_url.split("/")[-1].split(".")[0], "product_url": expected_url,
                    "title": item["name"].strip(), "image_url": image if isinstance(image, str) else None,
                    "display_price": decimal_text(offer.get("price")), "currency": currency,
                    "price_symbol": None, "currency_source": "json_ld" if currency else None,
                    "moq": None, "moq_text": None, "quantity_unit": None,
                    "price_basis": "structured_offer", "price_tiers": [],
                    "supplier_id": None, "supplier_name": seller.get("name") if isinstance(seller.get("name"), str) else None,
                    "supplier_url": supplier_url(seller.get("url", "")),
                    "supplier_years": None, "supplier_rating": None, "sales_text": None,
                    "marketing_tags": [], "is_sponsored": None, "verified_supplier": None,
                    "manufacturer": None, "extraction_source": "json_ld_product"}
    raise UnsupportedLayout("No supported 1688 detail DOM or identity-matched Product JSON-LD found.")


def parse_detail_dom(soup, expected_url):
    """Source: owner's saved public, not-logged-in product page (2026-10-19)."""
    offer_id = expected_url.split("/")[-1].split(".")[0]
    anchor = soup.select_one("#shopNavigation a.shop-company-name[href]")
    identity_ids = set()
    for link in soup.select("#shopNavigation a[href]"):
        if supplier_url(link.get("href", "")):
            identity_ids.update(parse_qs(urlsplit(link["href"]).query).get("offerId", []))
    if identity_ids != {offer_id}:
        raise UnsupportedLayout("Detail page identity does not match the requested offer ID.")
    price = soup.select_one("#mainPrice .price-info")
    amount = decimal_text(re.sub(r"\s+", "", "".join(text(n) for n in price.select(".currency"))) if price else "")
    title = text(soup.select_one("#productTitle h1"))
    if not title or amount is None:
        raise UnsupportedLayout("1688 detail title or main price is missing; page is not fully loaded or uses a different layout.")
    symbol = text(price.select_one(".currency-unit")) or None
    setting = page_currency(soup)
    explicit = {"US$": "USD", "USD": "USD", "CNY": "CNY", "RMB": "CNY", "EUR": "EUR", "€": "EUR", "£": "GBP"}.get(symbol)
    currency = explicit or setting
    if explicit and setting and explicit != setting:
        currency = None
    if symbol in {"¥", "￥"} and setting not in {"CNY", "JPY"}:
        currency = None  # Preserve ¥; don't confuse a yuan/yen symbol with an ISO code.
    if symbol == "$" and setting not in {"USD", "CAD", "AUD", "HKD"}:
        currency = None
    moq, moq_text, moq_scope, unit = None, None, None, None
    for node in soup.select("#productPromotion .coupon-list li"):
        value = text(node)
        match = re.fullmatch(r"(\d+)[-\s]*pieces?\s+mixed batch", value, re.I) or re.fullmatch(r"(\d+)\s*件混批", value)
        if match:
            moq, moq_text, moq_scope, unit = int(match[1]), value, "mixed_batch", "piece"
            break
    variants = []
    for node in soup.select("#skuSelection .expand-view-item"):
        label = text(node.select_one(".item-label"))
        prices = node.select(".item-price-stock")
        raw_price = text(prices[0]) if prices else ""
        matched = re.fullmatch(r"(US\$|USD|CNY|RMB|[¥￥$€£])\s*([0-9]+(?:\.[0-9]+)?)", raw_price)
        stock_node = node.select_one('od-text[i18n="sku-stock"]')
        stock, stock_unit = None, None
        if stock_node:
            try:
                values = json.loads(stock_node.get("data", "null"))
                if isinstance(values, list) and len(values) == 2 and re.fullmatch(r"[0-9]+", str(values[0])):
                    stock, stock_unit = int(values[0]), str(values[1])
            except (json.JSONDecodeError, TypeError):
                pass
        img = node.select_one("img[src]")
        if label:
            variants.append({"label": label, "display_price": matched[2] if matched else None,
                             "price_symbol": matched[1] if matched else None,
                             "currency": currency if matched and matched[1] == symbol else None,
                             "stock": stock, "stock_unit": stock_unit,
                             "image_url": img.get("src") if img else None})
    attributes = []
    for label in soup.select("#productAttributes .ant-descriptions-item-label"):
        content = label.find_next_sibling("td", class_="ant-descriptions-item-content")
        if text(label) and content:
            attributes.append({"name": text(label), "value": text(content)})
    gallery = list(dict.fromkeys(n.get("src") for n in soup.select("#gallery img.preview-img[src]") if n.get("src")))
    rating_node = soup.select_one("#productEvaluation .header-label-desc em.hl")
    rating = decimal_text(text(rating_node)) if rating_node and not hidden(rating_node) else None
    partial = bool(soup.select_one(".unlogin-lead, .od-sku-selection-not-login"))
    return {"product_id": offer_id, "product_url": expected_url, "title": title,
            "image_url": gallery[0] if gallery else None, "image_urls": gallery,
            "display_price": amount, "currency": currency, "price_symbol": symbol,
            "currency_source": "price_unit" if explicit and currency else "page_setting" if currency else None,
            "moq": moq, "moq_text": moq_text, "moq_scope": moq_scope, "quantity_unit": unit,
            "price_basis": "starting_price_with_variants" if variants else "detail_starting_price", "price_tiers": [],
            "variants": variants, "product_attributes": attributes,
            "product_rating": float(rating) if rating is not None and 0 <= float(rating) <= 5 else None,
            "supplier_id": None, "supplier_name": text(anchor.select_one("h1")) if anchor else None,
            "supplier_url": supplier_url(anchor.get("href", "")) if anchor else None,
            "supplier_years": None, "supplier_tenure_text": text(soup.select_one("#shopNavigation .shop-tp-year")) or None,
            "supplier_rating": None, "sales_text": None, "marketing_tags": [],
            "is_sponsored": None, "verified_supplier": None, "manufacturer": None,
            "detail_completeness": "public_partial" if partial else "visible_fields_only",
            "login_required_for_full_details": partial,
            "extraction_source": "1688_public_detail_dom"}
