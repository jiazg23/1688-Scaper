"""Strict shared validation for the Apify UI and API."""

import re
from dataclasses import dataclass
from urllib.parse import urlsplit


class InputError(ValueError):
    pass


def product_url(value: str) -> str:
    value = value.strip()
    if re.fullmatch(r"[0-9]{6,20}", value):
        return f"https://detail.1688.com/offer/{value}.html"
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == "https" and parts.hostname in
                 {"detail.1688.com", "m.1688.com", "www.1688.com"}
                 and parts.port in {None, 443} and not parts.username and not parts.password)
    except ValueError:
        valid = False
    match = re.fullmatch(r"/offer/([0-9]{6,20})\.html", parts.path) if valid else None
    if not match:
        raise InputError("Use an HTTPS 1688 /offer/123456789.html product URL or an offer ID, not a search/store URL.")
    return f"https://detail.1688.com/offer/{match[1]}.html"


def string_list(raw: dict, key: str, limit: int, default=()) -> list[str]:
    values = raw.get(key, list(default))
    if not isinstance(values, list) or len(values) > limit:
        raise InputError(f"{key} must be a list with at most {limit} entries.")
    if any(not isinstance(v, str) or not v.strip() or len(v) > 2048 for v in values):
        raise InputError(f"{key} entries must be non-empty strings, at most 2048 characters each.")
    return list(dict.fromkeys(v.strip() for v in values))


def integer(raw: dict, key: str, default: int, maximum: int) -> int:
    value = raw.get(key, default)
    if type(value) is not int or not 1 <= value <= maximum:
        raise InputError(f"{key} must be an integer between 1 and {maximum}.")
    return value


def boolean(raw: dict, key: str, default: bool) -> bool:
    value = raw.get(key, default)
    if type(value) is not bool:
        raise InputError(f"{key} must be true or false.")
    return value


@dataclass(frozen=True)
class Config:
    mode: str
    terms: list[str]
    offer_ids: list[str]
    max_products: int
    max_pages: int
    quantity: int
    use_proxy: bool
    proxy_country: str
    save_csv: bool
    csv_filename: str
    strict: bool

    @classmethod
    def parse(cls, raw):
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise InputError("Actor input must be a JSON object.")
        legacy_mode = raw.get("searchMode")
        if legacy_mode is not None and (not isinstance(legacy_mode, str) or legacy_mode not in {"keyword", "offer_ids"}):
            raise InputError("Image and search-link modes have been removed. Enter keywords or numeric offerIds; IDs take priority automatically.")
        for old_field in ("imageUrls", "uploadedImages", "searchUrls"):
            if raw.get(old_field):
                raise InputError(f"{old_field} is no longer supported. Enter keywords or numeric offerIds instead.")
        if raw.get("productUrls"):
            raise InputError("Paste only the product's numeric ID into offerIds, not a full product URL.")
        offer_ids = string_list(raw, "offerIds", 100)
        if any(not re.fullmatch(r"[0-9]{6,20}", value) for value in offer_ids):
            raise InputError("Offer IDs must contain 6–20 digits, such as 1071313125369. Do not paste full URLs.")
        # A prefilled keyword must not accidentally run when IDs are supplied.
        mode = "offer_ids" if offer_ids else "keyword"
        keyword_field = "keywords" if "keywords" in raw else "searchTerms"
        terms = [] if offer_ids else string_list(raw, keyword_field, 20, ["wireless earbuds"])
        if any(len(t) > 500 for t in terms):
            raise InputError("Each product keyword must be at most 500 characters.")
        if not offer_ids and not terms:
            raise InputError("Enter at least one search keyword or numeric Offer ID.")
        if raw.get("searchMode") == "offer_ids" and not offer_ids:
            raise InputError("Offer ID input needs at least one numeric offerIds entry.")
        country = raw.get("proxyCountryMode", "CN")
        if not isinstance(country, str) or country not in {"CN", "HK"}:
            raise InputError("Choose CN (China) or HK (Hong Kong). Automatic country rotation is not implemented; access failures stop the run.")
        if raw.get("sortBy", "relevance") != "relevance" or raw.get("merchantType", "any") != "any":
            raise InputError("This preview does not implement sorting or merchant filters. Use relevance and any.")
        for field in ("includeSkuDetails", "includeDescriptionHtml", "includeSupplierIntelligence"):
            if raw.get(field):
                raise InputError(f"{field} is not an implemented optional feature or paid add-on in this Actor.")
        filename = raw.get("csvFilename", "1688_products.csv")
        if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\.csv", filename):
            raise InputError("csvFilename must be a simple filename ending in .csv (letters, numbers, dots, underscores, hyphens).")
        if filename.lower() == "1688_suppliers.csv":
            raise InputError("1688_suppliers.csv is reserved for the supplier shortlist. Choose another product filename.")
        product_limit = "maxResults" if "maxResults" in raw else "maxProductsPerKeyword"
        page_limit = "maxPagesPerKeyword" if "maxPagesPerKeyword" in raw else "maxPagesText"
        return cls(mode=mode, terms=terms, offer_ids=offer_ids,
                   max_products=integer(raw, product_limit, 100, 10000), max_pages=integer(raw, page_limit, 5, 100),
                   quantity=integer(raw, "orderQuantity", 100, 10000000),
                   use_proxy=boolean(raw, "useApifyProxy", True), proxy_country=country,
                   save_csv=boolean(raw, "saveCsvFile", True), csv_filename=filename,
                   strict=boolean(raw, "failOnNoResults", False))
