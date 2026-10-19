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
    urls: list[str]
    images: list[str]
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
        if mode not in {"keyword", "image", "urls"}:
            raise InputError("searchMode must be keyword, image, or urls.")
        terms = string_list(raw, "searchTerms", 20, ["hair dryer"] if mode == "keyword" else [])
        if any(len(t) > 500 for t in terms):
            raise InputError("Each product keyword must be at most 500 characters.")
        urls = [product_url(u) for u in string_list(raw, "productUrls", 200)]
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
        if not {"keyword": terms, "urls": urls, "image": images}[mode]:
            raise InputError(f"{mode} mode needs at least one matching keyword, product URL, or image.")
        filename = raw.get("csvFilename", "1688_products.csv")
        if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\.csv", filename):
            raise InputError("csvFilename must be a simple filename ending in .csv (letters, numbers, dots, underscores, hyphens).")
        if filename.lower() == "1688_suppliers.csv":
            raise InputError("1688_suppliers.csv is reserved for the supplier shortlist. Choose another product filename.")
        return cls(
            mode, terms, list(dict.fromkeys(urls)), images,
            integer(raw, "maxProductsPerImage" if mode == "image" else "maxProductsPerKeyword", 50, 1000),
            integer(raw, "maxPagesImage" if mode == "image" else "maxPagesText", 5, 100),
            integer(raw, "orderQuantity", 100, 10000000),
            boolean(raw, "useApifyProxy", True), boolean(raw, "saveCsvFile", True), filename,
            boolean(raw, "failOnNoResults", False), boolean(raw, "skipFailedImages", True),
        )
