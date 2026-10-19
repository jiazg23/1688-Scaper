"""Strict shared validation for the Apify UI and API."""

import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


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


def search_url(value: str) -> str:
    """Preserve the query (keywords/filters/order/page) supplied by the user."""
    try:
        p = urlsplit(value.strip())
        supported = ((p.hostname == "air.1688.com" and p.path.rstrip("/") == "/kapp/1688-global/sales/search")
                     or (p.hostname == "s.1688.com" and p.path == "/selloffer/offer_search.htm"))
        valid = (p.scheme == "https" and supported and p.port in {None, 443}
                 and not p.username and not p.password and bool(p.query))
    except ValueError:
        valid = False
    if not valid:
        raise InputError("Paste the address of the 1688 tab showing product search results (air.1688.com/kapp/1688-global/sales/search?... or s.1688.com/selloffer/offer_search.htm?...), not the homepage, a login link, or an individual product link.")
    return urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))


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
    images: list[str]
    search_urls: list[str]
    max_products: int
    max_pages: int
    quantity: int
    use_proxy: bool
    save_csv: bool
    csv_filename: str
    strict: bool
    skip_failed_images: bool

    @classmethod
    def parse(cls, raw):
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise InputError("Actor input must be a JSON object.")
        mode = raw.get("searchMode", "keyword")
        if mode not in {"keyword", "image", "search_urls"}:
            raise InputError("Choose search_urls, keyword, or image. Individual product URL mode has been removed; search_urls accepts pages of search-result cards.")
        if raw.get("productUrls"):
            raise InputError("Individual product URLs are no longer supported. Paste the link to a page of product search results into searchUrls and choose searchMode: search_urls.")
        terms = string_list(raw, "searchTerms", 20, ["hair dryer"] if mode == "keyword" else [])
        if any(len(t) > 500 for t in terms):
            raise InputError("Each product keyword must be at most 500 characters.")
        search_urls = list(dict.fromkeys(search_url(u) for u in string_list(raw, "searchUrls", 20)))
        images = list(dict.fromkeys(string_list(raw, "uploadedImages", 20) + string_list(raw, "imageUrls", 20)))
        if len(images) > 20:
            raise InputError("Upload fields and imageUrls share a combined limit of 20 images.")
        for image in images:
            try:
                p = urlsplit(image)
                valid = p.scheme == "https" and p.hostname and not p.username and not p.password and p.port in {None, 443}
            except ValueError:
                valid = False
            if not valid:
                raise InputError("Images must be direct public HTTPS image URLs, not blob: URLs or website pages.")
        if not {"keyword": terms, "image": images, "search_urls": search_urls}[mode]:
            if mode == "search_urls":
                raise InputError("Search results links mode needs searchUrls. Search on 1688, copy the address from the new results tab, and paste it into Links to 1688 search results.")
            raise InputError(f"{mode} mode needs at least one matching keyword or product image.")
        filename = raw.get("csvFilename", "1688_products.csv")
        if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\.csv", filename):
            raise InputError("csvFilename must be a simple filename ending in .csv (letters, numbers, dots, underscores, hyphens).")
        if filename.lower() == "1688_suppliers.csv":
            raise InputError("1688_suppliers.csv is reserved for the supplier shortlist. Choose another product filename.")
        product_limit = {"image": "maxProductsPerImage", "search_urls": "maxProductsPerSearchUrl"}.get(mode, "maxProductsPerKeyword")
        page_limit = {"image": "maxPagesImage", "search_urls": "maxPagesPerSearchUrl"}.get(mode, "maxPagesText")
        return cls(mode=mode, terms=terms, images=images, search_urls=search_urls,
                   max_products=integer(raw, product_limit, 50, 1000), max_pages=integer(raw, page_limit, 5, 100),
                   quantity=integer(raw, "orderQuantity", 100, 10000000),
                   use_proxy=boolean(raw, "useApifyProxy", True), save_csv=boolean(raw, "saveCsvFile", True), csv_filename=filename,
                   strict=boolean(raw, "failOnNoResults", False), skip_failed_images=boolean(raw, "skipFailedImages", True))
